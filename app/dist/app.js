const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const STALE_MS = 10000;
const info = {
  soc_pct:['Charge level','%',0], pack_voltage_v:['Pack voltage','V',1], pack_current_a:['Pack current','A',1],
  speed_kmh:['Speed','km/h',1], battery_temp_c:['Battery temperature','°C',1], motor_temp_c:['Motor temperature','°C',1],
  controller_temp_c:['Controller temperature','°C',1], odometer_km:['Odometer','km',1],
  latitude:['Latitude','°',5],longitude:['Longitude','°',5],gps_accuracy_m:['GPS accuracy','m',1],satellites:['GPS satellites','',0]
};
const titleInfo = {live:['Overview','Know your Bee.','A clearer view of your bike, one signal at a time.'],
  battery:['Battery','Under the surface.','Look closer at the pack powering every ride.'],
  logs:['Rides & logs','Leave a trace.','Capture now. Understand more later.'],
  signals:['Signal explorer','Follow the signal.','Raw bytes, timestamps and evidence in one place.'],
  setup:['Connection & setup','Make the connection.','Local capture, lasting history, useful integrations.'],
  research:['What’s possible','Beyond the app.','A practical roadmap from CAN and GPS to owner-held data.']};
let mode = 'demo', page = 'live', running = true, tick = 0, history = [], latest = {}, token = '', device = 'ultra-bee';
let recording = null, selectedLog = null, replayIndex = null, nextBefore = null, sampleCount = 0, variant = 'Demo specimen';
let connectionError = '', lastPoll = 0, pollBusy = false, connectEpoch = 0, toastTimer, demoStart = Date.now();
let logs = [];
try { logs = JSON.parse(localStorage.getItem('beelink-demo-logs-v1') || '[]'); if (!Array.isArray(logs)) logs = []; } catch { logs = []; }

function toast(msg) { $('toast').textContent=msg; $('toast').hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>{$('toast').hidden=true;},5000); }
function label(key) { return info[key]?.[0] || (/^cell_\d+_v$/.test(key) ? `Cell group ${Number(key.split('_')[1])}` : key.replaceAll('_',' ')); }
function unit(key) { return info[key]?.[1] ?? (/^cell_\d+_v$/.test(key)?'V':''); }
function age(item) { return item ? Date.now()-Date.parse(item.timestamp) : Infinity; }
function stale(item) { return mode === 'live' && age(item)>STALE_MS; }
function value(key) { const item=latest[key]; if (!item || stale(item)) return '—'; return item.value.toFixed(info[key]?.[2] ?? (/^cell_\d+_v$/.test(key)?3:2)); }
function ageText(item) { if (!item) return 'Missing'; if (mode==='replay') return 'Recorded'; if(mode==='demo') return 'Simulated'; const seconds=Math.max(0,Math.floor(age(item)/1000)); return seconds<60?`${seconds}s ago`:`${Math.floor(seconds/60)}m ago`; }
function status(key) { const item=latest[key]; return !item?'Awaiting signal':stale(item)?`Stale · ${ageText(item)}`:`${item.confidence} · ${ageText(item)}`; }
function metric(key) { return `<div class="metric ${stale(latest[key])?'stale':''}"><div class="metric-top">${esc(label(key))}<span>↗</span></div><div class="metric-value">${value(key)}<small>${esc(unit(key))}</small></div><div class="metric-status">${esc(status(key))}</div></div>`; }
function applySample(sample) {
  for (const [key,item] of Object.entries(sample.signals||{})) {
    const old=latest[key];
    if (!old || Date.parse(sample.timestamp)>=Date.parse(old.timestamp)) latest[key]={...item,timestamp:sample.timestamp,source:sample.source,decoder_version:sample.decoder_version,variant:sample.variant};
  }
}
function demoSample() {
  const t=tick++, theta=t/35, speed=Math.max(0,31+13*Math.sin(t/13)+5*Math.sin(t/3));
  const signals={};
  const add=(key,v)=>{signals[key]={value:v,confidence:'simulated',evidence:'Synthetic preview · no CAN mapping'};};
  add('soc_pct', Math.max(0,68-t/500));add('pack_voltage_v',76.8-1.1*Math.sin(t/8)-speed/40);
  add('pack_current_a',12+speed/2+8*Math.sin(t/5));add('speed_kmh',speed);add('battery_temp_c',28+2*Math.sin(t/90));
  add('motor_temp_c',44+4*Math.sin(t/50));add('controller_temp_c',36+2*Math.sin(t/70));add('odometer_km',1250+t/120);
  add('latitude',51.45+0.006*Math.sin(theta));add('longitude',-0.55+0.01*Math.cos(theta)+0.003*Math.sin(theta*2));
  add('gps_accuracy_m',3.5+Math.sin(t/9));add('satellites',10);
  for(let n=1;n<=20;n++)add(`cell_${String(n).padStart(2,'0')}_v`,3.808+0.009*Math.sin(n*3.7)+0.001*Math.sin(t/13));
  return {schema_version:1,device_id:'demo-ultra-bee',capture_id:`demo-${demoStart}`,sequence:t,timestamp:new Date().toISOString(),variant:'Synthetic 20-group illustration',decoder_version:'demo-only',source:'demo',signals,frames:[]};
}
function seedDemo() {
  latest={};history=[];tick=0;demoStart=Date.now();
  // A short prelude makes the chart and route useful immediately; all points are marked demo.
  for(let i=0;i<75;i++) {const s=demoSample();s.timestamp=new Date(Date.now()-(74-i)*1000).toISOString();history.push(s);applySample(s);}
  sampleCount=history.length;variant='Demo specimen';
}
function switchPage() {
  page=location.hash.slice(1); if(!titleInfo[page])page='live';
  document.querySelectorAll('.page').forEach(el=>{el.hidden=el.id!==`page-${page}`;});
  document.querySelectorAll('nav a').forEach(el=>el.classList.toggle('active',el.dataset.page===page));
  const [name,title,subtitle]=titleInfo[page];$('page-name').textContent=name;$('title').textContent=title;$('subtitle').textContent=subtitle;
  render();
}
function route(points,target,index=null) {
  const positions=points.filter(s=>s.signals?.latitude&&s.signals?.longitude&&Number.isFinite(s.signals.latitude.value)&&Number.isFinite(s.signals.longitude.value));
  if(positions.length<2){$(target).innerHTML='<div class="route-empty">Waiting for a GPS route.<br>Coordinates come from the ESP32 GPS receiver.</div>';return positions;}
  // An equirectangular local sketch; not a navigation map.
  const lat0=positions.reduce((a,s)=>a+s.signals.latitude.value,0)/positions.length;
  const xy=positions.map(s=>[s.signals.longitude.value*Math.cos(lat0*Math.PI/180),s.signals.latitude.value]);
  const xs=xy.map(p=>p[0]),ys=xy.map(p=>p[1]);const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
  const W=600,H=260,scale=Math.min((W-80)/Math.max(maxX-minX,0.00001),(H-70)/Math.max(maxY-minY,0.00001));
  const project=p=>[W/2+(p[0]-(minX+maxX)/2)*scale,H/2-(p[1]-(minY+maxY)/2)*scale];
  const coords=xy.map(project),chosen=Math.min(coords.length-1,index??coords.length-1);
  let paths=[],segment=[];
  for(let i=0;i<coords.length;i++){if(i&&Date.parse(positions[i].timestamp)-Date.parse(positions[i-1].timestamp)>10000){paths.push(segment);segment=[];}segment.push(coords[i]);}paths.push(segment);
  const path=paths.map(ps=>`<polyline points="${ps.map(p=>p.join(',')).join(' ')}" fill="none" stroke="#ea763b" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>`).join('');
  const [cx,cy]=coords[chosen],[sx,sy]=coords[0];
  const simulated=positions.some(s=>s.source==='demo');
  $(target).innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${simulated?'Simulated':'Recorded'} GPS route with start and selected position"><text x="25" y="27" fill="#829179" font-size="10" letter-spacing="2">${simulated?'SIMULATED ROUTE':'RECORDED GPS'}</text>${path}<circle cx="${sx}" cy="${sy}" r="6" fill="#19372e" stroke="white" stroke-width="2"/><circle cx="${cx}" cy="${cy}" r="11" fill="#ec7833" opacity=".16"/><circle cx="${cx}" cy="${cy}" r="5" fill="#ed7736" stroke="white" stroke-width="2"/></svg>`;
  return positions;
}
function chart() {
  const key=$('chart-signal').value;
  const points=history.slice(-120).filter(s=>s.signals?.[key]).map(s=>[Date.parse(s.timestamp),s.signals[key].value]);
  if(points.length<2){$('live-chart').innerHTML='<div class="chart-empty">Waiting for more samples of this signal.</div>';return;}
  const W=1000,H=190,L=50,R=20,T=16,B=28,xmin=points[0][0],xmax=points.at(-1)[0];
  const values=points.map(p=>p[1]);let ymin=Math.min(...values),ymax=Math.max(...values);const pad=Math.max((ymax-ymin)*.15,.05);ymin-=pad;ymax+=pad;
  const pos=p=>[L+(p[0]-xmin)/Math.max(1,xmax-xmin)*(W-L-R),H-B-(p[1]-ymin)/(ymax-ymin)*(H-T-B)];
  let segments=[],seg=[];for(let i=0;i<points.length;i++){if(i&&points[i][0]-points[i-1][0]>STALE_MS){segments.push(seg);seg=[];}seg.push(pos(points[i]));}segments.push(seg);
  const lines=segments.map(s=>`<polyline points="${s.map(p=>p.join(',')).join(' ')}" fill="none" stroke="#d97c45" stroke-width="2.4"/>`).join('');
  const grids=Array.from({length:4},(_,i)=>{const y=T+i*(H-T-B)/3,v=ymax-i*(ymax-ymin)/3;return `<line x1="${L}" y1="${y}" x2="${W-R}" y2="${y}" stroke="#e5eadd" stroke-dasharray="3 4"/><text x="0" y="${y+3}" fill="#86927f" font-size="10">${v.toFixed(1)}</text>`;}).join('');
  const fmt=t=>new Date(t).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  $('live-chart').innerHTML=`<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(label(key))} chart in ${esc(unit(key))}">${grids}${lines}<text x="${L}" y="${H-3}" fill="#8a9683" font-size="10">${fmt(xmin)}</text><text x="${W-R}" y="${H-3}" text-anchor="end" fill="#8a9683" font-size="10">${fmt(xmax)}</text></svg>`;
}
function renderCommon() {
  const simulatedReplay=mode==='replay'&&history.some(s=>s.source==='demo');
  $('mode-pill').textContent=mode==='demo'?'Demo · simulated':mode==='replay'?(simulatedReplay?'Replay · simulated':'Replay · recorded'):connectionError?'Logger unavailable':'Local logger';
  $('mode-pill').className=`mode-pill ${mode==='live'&&!connectionError?'live':mode==='replay'?'replay':''}`;
  $('demo-toggle').hidden=mode!=='demo';$('demo-toggle').textContent=running?'Pause demo':'Resume demo';
  $('variant-label').textContent=variant;
  $('notice').innerHTML=mode==='demo'?'SIMULATED DATA <span>This is a working preview. No bike is connected and no CAN definitions are verified.</span>':mode==='replay'?(simulatedReplay?'SIMULATED REPLAY <span>This capture contains demo samples. No bike measurements are shown.</span>':'CAPTURE REPLAY <span>These are recorded samples. They are not current bike readings.</span>'):`LOCAL LOGGER <span>${esc(connectionError||'Logging is handled by the receiver, even when this page is closed. Signal freshness uses capture time, not upload time.')}</span>`;
  $('mode-button').textContent=mode==='live'?'Connection ↗':'Connect logger ↗';
  $('data-footnote').textContent=mode==='demo'?'Demo values are illustrations, not measurements or battery safety advice.':'Missing or stale readings do not establish the bike or battery is safe.';
}
function renderLive() {
  const soc=value('soc_pct');$('soc-big').innerHTML=soc==='—'?'—':`${soc}<em>%</em>`;
  $('gauge').style.setProperty('--fill',`${Math.max(0,Math.min(100,Number(soc)||0))*.8333}%`);
  $('soc-quality').textContent=latest.soc_pct?.confidence?.toUpperCase()||'AWAITING SIGNAL';
  $('capture-status').textContent=mode==='demo'?'Illustrative preview':mode==='replay'?'Recorded capture':`${sampleCount.toLocaleString()} samples stored`;
  $('last-update').textContent=ageText(latest.soc_pct);
  $('metrics').innerHTML=['pack_voltage_v','pack_current_a','speed_kmh','battery_temp_c','motor_temp_c','controller_temp_c','odometer_km','satellites'].map(metric).join('');
  route(history,'route-preview');
  const lat=value('latitude'),lon=value('longitude');$('gps-location').textContent=lat==='—'||lon==='—'?'Waiting for a fresh fix':`${lat}, ${lon}`;
  $('gps-accuracy').textContent=value('gps_accuracy_m')==='—'?'—':`${value('gps_accuracy_m')} m`;
  chart();
}
function renderBattery() {
  $('battery-metrics').innerHTML=['soc_pct','pack_voltage_v','pack_current_a','battery_temp_c'].map(metric).join('');
  const keys=Object.keys(latest).filter(k=>/^cell_\d+_v$/.test(k)).sort((a,b)=>Number(a.split('_')[1])-Number(b.split('_')[1]));
  $('cells').innerHTML=keys.length?keys.map(k=>`<div class="cell ${stale(latest[k])?'stale':''}" title="${esc(status(k))}"><span>GROUP ${Number(k.split('_')[1])}</span><strong>${value(k)} V</strong><div class="cell-bar" style="--height:${Math.min(100,Math.max(0,(latest[k].value-2.5)/1.8*100))}%"></div></div>`).join(''):'<p class="empty-state">No cell-group readings yet. The battery’s series-group count has not been assumed.</p>';
  const fresh=keys.length>1&&keys.every(k=>!stale(latest[k]))&&keys.every(k=>latest[k].timestamp===latest[keys[0]].timestamp);
  const volts=keys.map(k=>latest[k].value);
  $('cell-spread').textContent=fresh?`${Math.round((Math.max(...volts)-Math.min(...volts))*1000)} mV SPREAD`:'SPREAD UNAVAILABLE';
}
function renderSignals() {
  const filter=$('signal-filter').value.toLowerCase();
  const rows=Object.keys(latest).filter(k=>`${label(k)} ${k}`.toLowerCase().includes(filter)).sort();
  $('signal-table').innerHTML=rows.map(k=>{const s=latest[k];return `<tr><td>${esc(label(k))}<small class="monospace">${esc(k)}</small></td><td>${value(k)} ${esc(unit(k))}${stale(s)?`<small>Last recorded: ${s.value.toFixed(3)}</small>`:''}</td><td>${esc(ageText(s))}<small>${esc(s.timestamp)}</small></td><td><span class="status-label ${esc(s.confidence)}">${esc(s.confidence)}</span><small>${esc(s.evidence)}</small></td><td>${esc(s.source)}<small>${esc(s.decoder_version)}</small></td></tr>`;}).join('')||'<tr><td colspan="5">No matching signals. Raw capture can be logged before signals are decoded.</td></tr>';
  const frames=history.flatMap(s=>(s.frames||[]).map(f=>({...f,timestamp:f.timestamp||s.timestamp}))).slice(-50).reverse();
  $('frame-table').innerHTML=frames.map(f=>`<tr><td>${esc(f.timestamp)}</td><td class="monospace">0x${Number(f.id).toString(16).toUpperCase()}</td><td>${f.extended?'Extended 29-bit':'Standard 11-bit'}</td><td>${f.dlc}</td><td class="monospace">${esc(f.data)}</td></tr>`).join('')||'<tr><td colspan="5">No raw CAN frames. The demo invents no protocol identifiers.</td></tr>';
}
function saveLogs() {
  // Browser persistence is only a bounded demo convenience; the real logger uses SQLite.
  try{localStorage.setItem('beelink-demo-logs-v1',JSON.stringify(logs));}catch{toast('Browser storage is full. Export the demo session before closing this page.');}
}
function logData() { return selectedLog?.samples || history; }
function stats(samples) {
  if(!samples.length)return {count:0,duration:0,distance:null};
  let distance=0,haveDistance=false;
  for(let i=1;i<samples.length;i++){
    const dt=(Date.parse(samples[i].timestamp)-Date.parse(samples[i-1].timestamp))/1000;
    const a=samples[i-1].signals?.speed_kmh,b=samples[i].signals?.speed_kmh;
    if(a&&b&&dt>0&&dt<=10){distance+=(a.value+b.value)/2*dt/3600;haveDistance=true;}
  }
  return {count:samples.length,duration:Math.max(0,(Date.parse(samples.at(-1).timestamp)-Date.parse(samples[0].timestamp))/1000),distance:haveDistance?distance:null};
}
function renderLogs() {
  $('record-button').hidden=mode!=='demo';$('record-button').textContent=recording?'Stop recording':'Record demo';
  $('log-explanation').textContent=mode==='live'?'The receiver writes every accepted sample to SQLite. The ESP32 should keep its own SD log while away from Wi-Fi.':'Record a demo session or replay a saved JSON / JSONL capture.';
  $('load-history').hidden=mode!=='live';$('load-history').disabled=!nextBefore;
  const data=logData(),st=stats(data);
  $('log-summary').innerHTML=`<div class="metric"><div class="metric-top">Loaded samples</div><div class="metric-value">${st.count.toLocaleString()}</div><div class="metric-status">${mode==='live'?`${sampleCount.toLocaleString()} stored in logger`:'Demo / imported capture'}</div></div><div class="metric"><div class="metric-top">Capture span</div><div class="metric-value">${(st.duration/60).toFixed(1)}<small>min</small></div><div class="metric-status">Gaps remain in the record</div></div><div class="metric"><div class="metric-top">Distance from speed</div><div class="metric-value">${st.distance===null?'—':st.distance.toFixed(2)}<small>km</small></div><div class="metric-status">Estimate · intervals ≤ 10 seconds only</div></div>`;
  const list=[...(selectedLog&&selectedLog.id==='imported'?[selectedLog]:[]),...logs];
  $('log-list').innerHTML=mode==='live'?`<div class="log-item"><span class="log-icon">≋</span><div class="log-details"><b>${esc(device)} · local database</b><small>${sampleCount.toLocaleString()} samples persisted · ${history.length.toLocaleString()} loaded in this page</small></div><span class="tag">SQLITE</span></div>`:list.map((log,i)=>`<div class="log-item"><span class="log-icon">↗</span><div class="log-details"><b>${esc(log.name)}</b><small>${log.samples.length} samples · ${esc(log.samples[0]?.timestamp||'Empty capture')}</small></div><span class="tag">${log.samples.some(s=>s.source==='demo')?'SIMULATED':'IMPORTED'}</span><button class="secondary replay-log" data-index="${i}">Replay</button></div>`).join('')||'<div class="empty-state">Your capture library starts here.<br>Record the demo to try logging, or import a capture from your future ESP32 gateway.</div>';
  document.querySelectorAll('.replay-log').forEach(b=>{b.onclick=()=>{selectCapture(list[Number(b.dataset.index)]);};});
  const positions=route(data,'replay-route',replayIndex);const slider=$('replay-position');slider.max=Math.max(0,positions.length-1);slider.disabled=!positions.length;slider.value=replayIndex??slider.max;
  const at=positions[Math.min(positions.length-1,replayIndex??positions.length-1)];$('replay-time').textContent=at?new Date(at.timestamp).toLocaleString():'No position samples';
  $('replay-caption').textContent=selectedLog?'SELECTED CAPTURE':mode==='demo'?'SIMULATED STREAM':'LOADED HISTORY';
  $('export-note').textContent=mode==='live'?'Exports download the complete device log from SQLite, including raw frames in JSONL. CSV contains decoded readings.':'Exports use the selected capture, or the recent stream. Demo samples remain marked source: demo.';
  $('export-json').disabled=!data.length&&mode!=='live';$('export-csv').disabled=!data.length&&mode!=='live';
}
function render() {renderCommon();if(page==='live')renderLive();if(page==='battery')renderBattery();if(page==='signals')renderSignals();if(page==='logs')renderLogs();}
function stopRecord(){if(!recording)return;const r=recording;recording=null;if(r.samples.length){logs.unshift(r);logs=logs.slice(0,3);saveLogs();toast('Demo capture saved in this browser. Export for a portable copy.');}else toast('No samples were recorded.');}
function startDemo(){stopRecord();connectEpoch++;mode='demo';running=true;connectionError='';selectedLog=null;replayIndex=null;seedDemo();render();$('connection-message').textContent='Using simulated data. No samples are sent to the real logger.';}
function selectCapture(log){stopRecord();connectEpoch++;history=[...log.samples].sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));selectedLog={...log,samples:history};mode='replay';running=false;latest={};history.forEach(applySample);variant=history.at(-1)?.variant||'Imported capture';replayIndex=null;render();}
async function api(path) {const response=await fetch(path,{headers:token?{Authorization:`Bearer ${token}`}:{},cache:'no-store',signal:AbortSignal.timeout(6000)});if(!response.ok){const err=await response.json().catch(()=>({}));throw new Error(err.error||`Logger returned ${response.status}`);}return response;}
async function connect(){
  stopRecord();const epoch=++connectEpoch;token=$('access-token').value;$('access-token').value='';device=$('device-id').value.trim()||'ultra-bee';
  $('connection-message').textContent='Connecting…';$('connect-button').disabled=true;
  try {
    const snap=await (await api(`/api/snapshot?device=${encodeURIComponent(device)}`)).json();
    const hist=await (await api(`/api/history?device=${encodeURIComponent(device)}&limit=1000`)).json();
    if(epoch!==connectEpoch)return;
    if(!snap.signals||!Array.isArray(hist.samples))throw new Error('This page is not served by the Bee Link local receiver.');
    mode='live';selectedLog=null;running=false;latest=snap.signals;sampleCount=snap.sample_count;variant=snap.variant;history=hist.samples.sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));nextBefore=hist.next_before;connectionError='';lastPoll=Date.now();
    $('connection-message').textContent=`Connected. ${sampleCount} samples stored for ${device}. Waiting for fresh CAN / GPS if the bike is offline.`;
    toast('Local logger connected.');render();
  }catch(e){if(epoch===connectEpoch){$('connection-message').textContent=`Connection failed: ${e.message} Start server.py and open its local URL. Current preview remains available.`;toast('Could not connect to the local receiver.');}}
  finally{$('connect-button').disabled=false;}
}
async function poll(){
  if(mode!=='live'||pollBusy)return;pollBusy=true;const epoch=connectEpoch;
  try{const snap=await(await api(`/api/snapshot?device=${encodeURIComponent(device)}`)).json();if(epoch!==connectEpoch)return;
    if(snap.sample_count!==sampleCount){const hist=await(await api(`/api/history?device=${encodeURIComponent(device)}&limit=1000`)).json();if(epoch!==connectEpoch)return;history=hist.samples.sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));nextBefore=hist.next_before;}
    latest=snap.signals;sampleCount=snap.sample_count;variant=snap.variant;connectionError='';
  }catch(e){if(epoch===connectEpoch)connectionError=`Logger unavailable: ${e.message}. Readings age naturally; logging depends on the receiver staying running.`;}finally{pollBusy=false;if(epoch===connectEpoch)render();}
}
function validateImported(s){
  if(!s||s.schema_version!==1||!['can','gnss','mixed','demo'].includes(s.source)||typeof s.timestamp!=='string'||!/(Z|[+-]\d\d:\d\d)$/.test(s.timestamp)||!Number.isFinite(Date.parse(s.timestamp)))throw new Error('Every sample needs schema_version 1, source and a timestamp with timezone.');
  if(!Number.isSafeInteger(s.sequence)||s.sequence<0)throw new Error('Invalid capture sequence.');
  for(const k of ['device_id','capture_id','variant','decoder_version'])if(typeof s[k]!=='string'||!s[k].length||s[k].length>128)throw new Error(`Invalid ${k}.`);
  if(!s.signals||typeof s.signals!=='object'||Array.isArray(s.signals)||Object.keys(s.signals).length>128)throw new Error('Invalid signals object.');
  for(const [k,v]of Object.entries(s.signals)){if(!/^[a-z][a-z0-9_]{0,63}$/.test(k)||!v||!Number.isFinite(v.value)||!['simulated','provisional','verified'].includes(v.confidence)||typeof v.evidence!=='string')throw new Error('Each signal needs a finite value, confidence and evidence.');if((k==='latitude'&&Math.abs(v.value)>90)||(k==='longitude'&&Math.abs(v.value)>180))throw new Error('Invalid GPS coordinates.');}
  if(!Array.isArray(s.frames)||s.frames.length>1000)throw new Error('Invalid frame list.');
  for(const f of s.frames){if(typeof f.extended!=='boolean'||!Number.isInteger(f.id)||f.id<0||f.id>(f.extended?0x1fffffff:0x7ff)||!/^([0-9a-f]{2}){0,8}$/i.test(f.data)||f.dlc!==f.data.length/2)throw new Error('Invalid classical CAN frame.');if(f.timestamp&&!Number.isFinite(Date.parse(f.timestamp)))throw new Error('Invalid frame timestamp.');}
  return s;
}
async function importCapture(file){if(!file)return;try{
  if(file.size>10*1024*1024)throw new Error('Replay imports are limited to 10 MB. Keep larger captures in the local logger.');
  const text=await file.text();let input;
  try{const json=JSON.parse(text);input=Array.isArray(json)?json:(json.samples||[json]);}catch{input=text.split(/\r?\n/).filter(l=>l.trim()).map(l=>JSON.parse(l));}
  if(!Array.isArray(input)||!input.length||input.length>20000)throw new Error('Import 1–20,000 samples at a time.');
  const samples=input.map(validateImported);const devices=new Set(samples.map(s=>s.device_id));if(devices.size>1)throw new Error('Replay one device per capture to avoid combining different bikes.');
  selectCapture({id:'imported',name:file.name,samples});location.hash='logs';toast('Capture imported for replay only. The real database was not changed.');
}catch(e){toast(`Import failed: ${e.message}`);}finally{$('import-file').value='';}}
function download(text,name,type){const blob=text instanceof Blob?text:new Blob([text],{type});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function csvEscape(v){let str=String(v??'');if(/^[=+\-@]/.test(str)&&typeof v==='string')str="'"+str;return '"'+str.replaceAll('"','""')+'"';}
async function exportData(format){try{
  if(mode==='live'){const response=await api(`/api/export.${format}?device=${encodeURIComponent(device)}`);download(await response.blob(),`bee-link-${device.replace(/[^a-z0-9_-]/gi,'_')}.${format}`);return;}
  const data=logData();if(!data.length)return;
  if(format==='jsonl')download(data.map(s=>JSON.stringify(s)).join('\n')+'\n','bee-link-capture.jsonl','application/x-ndjson');
  else{const rows=[['timestamp_utc','device_id','capture_id','sequence','variant','decoder_version','source','signal','value','confidence','evidence']];for(const s of data)for(const[k,v]of Object.entries(s.signals||{}))rows.push([s.timestamp,s.device_id,s.capture_id,s.sequence,s.variant,s.decoder_version,s.source,k,v.value,v.confidence,v.evidence]);download(rows.map(r=>r.map(csvEscape).join(',')).join('\r\n'),'bee-link-readings.csv','text/csv');}
}catch(e){toast(`Export failed: ${e.message}`);}}

$('mode-button').onclick=()=>{location.hash='setup';};$('demo-toggle').onclick=()=>{running=!running;render();};$('start-demo').onclick=startDemo;$('connect-button').onclick=connect;
$('record-button').onclick=()=>{if(recording)stopRecord();else{recording={id:`demo-log-${Date.now()}`,name:`Demo ride · ${new Date().toLocaleString()}`,samples:[]};selectedLog=null;running=true;toast('Recording simulated samples in this browser.');}render();};
$('import-button').onclick=()=>{$('import-file').click();};$('import-file').onchange=e=>{importCapture(e.target.files[0]);};
$('export-json').onclick=()=>{exportData('jsonl');};$('export-csv').onclick=()=>{exportData('csv');};$('chart-signal').onchange=chart;$('signal-filter').oninput=renderSignals;
$('replay-position').oninput=e=>{replayIndex=Number(e.target.value);if(mode==='replay'){const positions=logData().filter(s=>s.signals?.latitude&&s.signals?.longitude);const until=Date.parse(positions[replayIndex]?.timestamp);latest={};history.filter(s=>Date.parse(s.timestamp)<=until).forEach(applySample);}renderLogs();};$('refresh-logs').onclick=()=>{mode==='live'?poll():renderLogs();};
$('load-history').onclick=async()=>{if(!nextBefore)return;const epoch=connectEpoch;try{const hist=await(await api(`/api/history?device=${encodeURIComponent(device)}&limit=1000&before=${nextBefore}`)).json();if(epoch!==connectEpoch)return;history=[...hist.samples,...history].sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp));nextBefore=hist.next_before;render();}catch(e){toast(e.message);}};
window.addEventListener('hashchange',switchPage);window.addEventListener('pagehide',stopRecord);
seedDemo();switchPage();
setInterval(()=>{
  if(mode==='demo'&&running){const s=demoSample();applySample(s);history.push(s);if(history.length>2000)history.shift();sampleCount=history.length;if(recording){recording.samples.push(s);if(recording.samples.length>=2000)stopRecord();}render();}
  else if(mode==='live'){if(Date.now()-lastPoll>=1000){lastPoll=Date.now();poll();}render();}
},1000);
