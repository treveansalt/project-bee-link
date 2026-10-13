"""Optional low-rate MeshCore companion bridge. Disabled on every startup."""
import asyncio
import importlib.util
import os
import random
import re
import threading
import time
from datetime import datetime, timezone

from meshcore_policy import format_telemetry


def radio_settings():
    """Radio configuration is local operator configuration, never browser secrets."""
    transport = os.environ.get('BEELINK_MESHCORE_TRANSPORT', 'serial')
    address = os.environ.get('BEELINK_MESHCORE_ADDRESS', '').strip()
    contact = os.environ.get('BEELINK_MESHCORE_CONTACT', '').strip().lower()
    channel = os.environ.get('BEELINK_MESHCORE_CHANNEL', '')
    if transport not in {'serial', 'tcp', 'ble'} or not address:
        raise ValueError('Configure the MeshCore transport and radio address first.')
    port = int(os.environ.get('BEELINK_MESHCORE_PORT', '4000'))
    if not 1 <= port <= 65535:
        raise ValueError('Invalid radio TCP port.')
    if channel:
        index = int(channel)
        if not 1 <= index <= 7 or os.environ.get('BEELINK_MESHCORE_PRIVATE_CHANNEL') != '1':
            raise ValueError('Use a deliberately configured private channel 1-7; public channel 0 is excluded.')
        if contact:
            raise ValueError('Choose one destination: a contact or a private channel.')
        return dict(transport=transport, address=address, port=port, channel=index)
    if not re.fullmatch('[0-9a-f]{64}', contact):
        raise ValueError('Configure the recipient contact full 64-character public key.')
    return dict(transport=transport, address=address, port=port, contact=contact)


async def transmit(config, make_message, permitted):
    """One submission; never invoke automatic text retries or change radio settings."""
    from meshcore import MeshCore, EventType
    radio = None
    try:
        args = dict(debug=False, auto_reconnect=False, default_timeout=10)
        if config['transport'] == 'serial':
            connect = MeshCore.create_serial(config['address'], **args)
        elif config['transport'] == 'tcp':
            connect = MeshCore.create_tcp(config['address'], config['port'], **args)
        else:
            connect = MeshCore.create_ble(config['address'], **args)
        radio = await asyncio.wait_for(connect, 30)
        if radio is None:
            raise RuntimeError('Radio connection failed.')
        if 'contact' in config:
            contacts = await asyncio.wait_for(radio.commands.get_contacts(), 15)
            if contacts.type != EventType.CONTACTS:
                raise RuntimeError('Cannot read radio contacts.')
            contact = contacts.payload.get(config['contact'])
            if contact is None:
                raise RuntimeError('Recipient is not in this radio contact list.')
            if not permitted():
                return 'cancelled'
            message = make_message()
            if not message:
                return 'skipped: no fresh verified telemetry'
            result = await asyncio.wait_for(radio.commands.send_msg(contact, message), 15)
            expected = EventType.MSG_SENT
        else:
            if not permitted():
                return 'cancelled'
            message = make_message()
            if not message:
                return 'skipped: no fresh verified telemetry'
            result = await asyncio.wait_for(radio.commands.send_chan_msg(config['channel'], message), 15)
            expected = EventType.OK
        if result is None or result.type != expected:
            raise RuntimeError('Radio rejected the submission.')
        return 'submitted'  # Radio acceptance is not a delivery acknowledgement.
    finally:
        if radio is not None:
            try:
                await asyncio.wait_for(radio.disconnect(), 5)
            except Exception:
                pass


class MeshCoreService:
    def __init__(self, store, sender=None, clock=time.monotonic, jitter=None):
        self.store = store
        self.sender = sender
        self.clock = clock
        self.jitter = jitter or (lambda: random.uniform(0, 60))
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.thread = None
        self.settings = dict(enabled=False, include_location=False, interval_minutes=15, device='ultra-bee')
        self.revision = 0
        self.next_due = None
        self.last_attempt = None
        self.last_submission = None
        self.outcome = 'disabled'
        self.busy = False

    def status(self):
        with self.lock:
            try:
                radio_settings()
                configured = True
            except (ValueError, TypeError):
                configured = False
            installed = self.sender is not None or importlib.util.find_spec('meshcore') is not None
            return {**self.settings, 'radio_configured': configured, 'dependency_installed': installed,
                    'next_attempt_in_seconds': max(0, round(self.next_due-self.clock())) if self.next_due is not None else None,
                    'last_attempt': self.last_attempt, 'last_submission': self.last_submission,
                    'status': self.outcome, 'busy': self.busy}

    def configure(self, body):
        if not isinstance(body, dict) or set(body) - set(self.settings):
            raise ValueError('Unsupported MeshCore settings.')
        with self.lock:
            candidate = {**self.settings, **body}
            if type(candidate['enabled']) is not bool or type(candidate['include_location']) is not bool:
                raise ValueError('Enabled and location sharing must be booleans.')
            minutes = candidate['interval_minutes']
            if type(minutes) is not int or not 15 <= minutes <= 1440:
                raise ValueError('Interval must be a whole number from 15 to 1440 minutes.')
            if not isinstance(candidate['device'], str) or not re.fullmatch('[a-zA-Z0-9_-]{1,64}', candidate['device']):
                raise ValueError('Invalid device identifier.')
            if candidate['enabled']:
                if self.sender is None:
                    radio_settings()
                    if importlib.util.find_spec('meshcore') is None:
                        raise ValueError('Install requirements-meshcore.txt on the receiver first.')
            if candidate != self.settings:
                self.settings = candidate
                self.revision += 1
                self.next_due = self.clock()+minutes*60+self.jitter() if candidate['enabled'] else None
                self.outcome = 'waiting' if candidate['enabled'] else 'disabled'
            return self.status()

    def poll(self):
        with self.lock:
            if not self.settings['enabled'] or self.busy or self.next_due is None or self.clock() < self.next_due:
                return
            settings = dict(self.settings)
            revision = self.revision
            self.next_due = self.clock()+settings['interval_minutes']*60+self.jitter()
            self.busy = True
            self.last_attempt = datetime.now(timezone.utc).isoformat()
        def permitted():
            with self.lock:
                return self.settings['enabled'] and self.revision == revision and not self.stop.is_set()
        try:
            snapshot = self.store.snapshot(settings['device'])
            message = format_telemetry(snapshot, include_location=settings['include_location'])
            if not permitted():
                outcome = 'cancelled'
            elif not message:
                outcome = 'skipped: no fresh verified telemetry'
            elif self.sender:
                outcome = self.sender(message, permitted)
            else:
                def fresh_message():
                    return format_telemetry(self.store.snapshot(settings['device']), include_location=settings['include_location'])
                outcome = asyncio.run(transmit(radio_settings(), fresh_message, permitted))
            with self.lock:
                if outcome == 'submitted':
                    self.last_submission = datetime.now(timezone.utc).isoformat()
                if revision == self.revision:
                    self.outcome = outcome
        except Exception:
            with self.lock:
                if revision == self.revision:
                    self.outcome = 'failed: check radio configuration and connection'
        finally:
            with self.lock:
                self.busy = False

    def start(self):
        def run():
            while not self.stop.wait(1):
                self.poll()
        self.thread = threading.Thread(target=run, name='beelink-meshcore', daemon=True)
        self.thread.start()

    def close(self):
        with self.lock:
            self.settings['enabled'] = False
            self.revision += 1
            self.next_due = None
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)
