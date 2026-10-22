"""Apply the Bee-Link overlay to an explicitly named, clean pinned MeshCore clone."""
import argparse
from pathlib import Path
import shutil
import subprocess

UPSTREAM = 'a366955cb2f67b8e6842d4f00d2b6a554dddd88a'

def prepare(root):
    root = Path(root).resolve()
    revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != UPSTREAM:
        raise ValueError('Use the documented pinned MeshCore revision.')
    if subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip():
        raise ValueError('Use a clean, disposable MeshCore clone; this overlay edits its source.')
    here = Path(__file__).resolve().parent
    dst = root / 'examples/companion_radio'
    main = dst / 'main.cpp'
    mesh = dst / 'MyMesh.cpp'
    main_text = main.read_text()
    mesh_text = mesh.read_text()
    anchors = ['#include "MyMesh.h"', '  board.onBootComplete();', '  the_mesh.loop();']
    if any(main_text.count(anchor) != 1 for anchor in anchors) or mesh_text.count('void MyMesh::handleCmdFrame(size_t len) {') != 1:
        raise ValueError('Upstream overlay anchors changed; inspect rather than guessing.')
    main_text = main_text.replace(anchors[0], anchors[0]+'\n#include "BeeLinkRuntime.h"')
    main_text = main_text.replace(anchors[1], '  beeLinkBegin();\n'+anchors[1])
    main_text = main_text.replace(anchors[2], anchors[2]+'\n  beeLinkLoop();')
    mesh_text = mesh_text.replace('#include "MyMesh.h"', '#include "MyMesh.h"\n#include "BeeLinkRuntime.h"', 1)
    mesh_text = mesh_text.replace('void MyMesh::handleCmdFrame(size_t len) {', '''void MyMesh::handleCmdFrame(size_t len) {
  uint8_t bee_reply[12];
  size_t bee_size = beeLinkCommand(cmd_frame, len, bee_reply);
  if (bee_size) { _serial->writeFrame(bee_reply, bee_size); return; }''', 1)
    for name in ['IntervalGate.h','TelemetryPolicy.h','BeeLinkRuntime.h','BeeLinkRuntime.cpp']:
        shutil.copyfile(here / name, dst / name)
    main.write_text(main_text)
    mesh.write_text(mesh_text)
    (root / 'platformio.local.ini').write_text('''[env:BeeLink_Xiao_S3_WIO]
extends = Xiao_S3_WIO
build_flags =
  ${Xiao_S3_WIO.build_flags}
  -D MAX_CONTACTS=32
  -D MAX_GROUP_CHANNELS=8
  -D OFFLINE_QUEUE_SIZE=16
  -D ENABLE_USB_INTERFACE
  -UENABLE_ADVERT_ON_BOOT
  -DENABLE_ADVERT_ON_BOOT=0
  -UENABLE_PRIVATE_KEY_EXPORT
build_src_filter = ${Xiao_S3_WIO.build_src_filter}
  +<../examples/companion_radio/*.cpp>
  +<helpers/ui/NullDisplayDriver.cpp>
  +<helpers/esp32/*.cpp>
lib_deps =
  ${Xiao_S3_WIO.lib_deps}
  densaugeo/base64 @ 1.4.0
  mikalhart/TinyGPSPlus @ 1.1.0
''')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('clone', help='Clean disposable MeshCore clone at the pinned revision')
    args = parser.parse_args()
    prepare(args.clone)
    print('Overlay prepared. GNSS reset isolation acknowledgement is required before compilation.')
