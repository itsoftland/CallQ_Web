"""
Firebase Cloud Messaging (FCM) service utility for sending push notifications to Android TV devices.
Uses Firebase Admin SDK for sending notifications.

IIS-safe design:
  - Named app 'callq' to avoid conflicts with other Firebase projects on the same server.
  - Blocking send() calls run in a **module-level ThreadPoolExecutor** (non-daemon, max 4 workers).
    Unlike daemon threads, executor threads are NOT killed when IIS recycles the worker process —
    they always run to completion so the success/error log always appears.
  - atexit handler shuts down the executor cleanly when the process exits.
"""
import atexit
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict, Any
from django.conf import settings
from .models import Device

# Top-level import — same pattern as the working reference implementation.
# If firebase_admin is not installed this will raise ImportError at startup,
# which is intentional (the package must be present for FCM to work).
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    _FIREBASE_ADMIN_AVAILABLE = True
except ImportError:
    _FIREBASE_ADMIN_AVAILABLE = False

# Dedicated FCM logger — writes to fcm.log (DEBUG+) and also mirrors to actions.log
logger = logging.getLogger('fcm')

# Module-level cached app reference
_firebase_app = None
_CALLQ_APP_NAME = 'callq'

# ---------------------------------------------------------------------------
# Module-level ThreadPoolExecutor — non-daemon, survives IIS process recycle
# ---------------------------------------------------------------------------

_fcm_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='fcm-worker')


def _shutdown_executor():
    """Drain the executor on interpreter shutdown (registered via atexit)."""
    try:
        _fcm_executor.shutdown(wait=True, cancel_futures=False)
        logger.info("[FCM] Executor shut down cleanly.")
    except Exception as e:
        logger.error(f"[FCM] Error during executor shutdown: {e}")


atexit.register(_shutdown_executor)


# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

def get_firebase_app():
    """Get or initialize the CallQ-specific named Firebase Admin SDK app.

    Uses a named app ('callq') instead of the default app to avoid conflicts
    with other projects on the same server that may have already claimed the
    default Firebase app with different credentials.
    """
    global _firebase_app

    if not _FIREBASE_ADMIN_AVAILABLE:
        logger.error(
            "firebase-admin package is NOT installed. Run: pip install firebase-admin"
        )
        return None

    if _firebase_app is not None:
        return _firebase_app

    # Check if the named app is already registered (e.g. after a hot-reload)
    try:
        _firebase_app = firebase_admin.get_app(_CALLQ_APP_NAME)
        logger.info(f"Firebase Admin SDK named app '{_CALLQ_APP_NAME}' already initialized, reusing.")
        return _firebase_app
    except ValueError:
        pass  # Not initialized yet — continue below

    credentials_path = getattr(settings, 'FCM_CREDENTIALS_PATH', '')
    project_id = getattr(settings, 'FCM_PROJECT_ID', '')

    logger.info(f"FCM init: credentials_path='{credentials_path}', project_id='{project_id}'")

    if not credentials_path:
        logger.error(
            "FCM_CREDENTIALS_PATH is not set in .env. "
            "Cannot initialize Firebase — no fallback to default app (other projects may own it)."
        )
        return None

    file_exists = os.path.exists(credentials_path)
    logger.info(f"FCM credentials file exists: {file_exists} (path: {credentials_path})")

    if not file_exists:
        logger.error(
            f"FCM credentials file NOT FOUND at path: '{credentials_path}'. "
            f"Check FCM_CREDENTIALS_PATH in .env"
        )
        return None

    try:
        cred = credentials.Certificate(credentials_path)
        _firebase_app = firebase_admin.initialize_app(
            cred,
            {'projectId': project_id or None},
            name=_CALLQ_APP_NAME,
        )
        logger.info(
            f"Firebase Admin SDK named app '{_CALLQ_APP_NAME}' initialized successfully "
            f"with credentials from '{credentials_path}' (projectId='{project_id}')"
        )
        return _firebase_app
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Internal worker functions — submitted to the thread-pool executor
# ---------------------------------------------------------------------------

def _do_send_single(serial: str, message_obj, firebase_app, device_id: int):
    """Blocking single-device FCM send — runs inside the thread pool."""
    try:
        logger.info(f"[FCM] [thread] Calling messaging.send() for '{serial}' ...")
        response = messaging.send(message_obj, app=firebase_app)
        logger.info(f"[FCM] ✓ Notification sent to '{serial}'. Firebase message ID: {response}")

    except messaging.UnregisteredError:
        logger.warning(
            f"[FCM] Token is UNREGISTERED for device '{serial}'. Clearing stale token from DB."
        )
        try:
            from .models import Device as _Device
            dev = _Device.objects.get(id=device_id)
            dev.fcm_token = None
            dev.save(update_fields=['fcm_token'])
        except Exception as db_err:
            logger.error(f"[FCM] Could not clear stale token for '{serial}': {db_err}")

    except messaging.SenderIdMismatchError as e:
        logger.error(
            f"[FCM] SenderIdMismatch for device '{serial}': {str(e)}. "
            f"Check that the serviceAccountKey.json matches the Firebase project."
        )

    except messaging.InvalidArgumentError as e:
        logger.error(f"[FCM] InvalidArgument for device '{serial}': {str(e)}")

    except Exception as e:
        logger.error(
            f"[FCM] Unexpected error sending to device '{serial}': {str(e)}",
            exc_info=True,
        )


def _do_send_multicast(tokens: List[str], multicast_msg, firebase_app, device_map: dict):
    """Blocking multicast FCM send using MulticastMessage — runs inside the thread pool.

    Mirrors the reference implementation:
        response = messaging.send_each_for_multicast(message)
    """
    try:
        logger.info(
            f"[FCM] [thread] Calling messaging.send_each_for_multicast() "
            f"for {len(tokens)} device(s) ..."
        )
        response = messaging.send_each_for_multicast(multicast_msg, app=firebase_app)

        success_count = response.success_count
        failure_count = len(response.responses) - success_count

        logger.info(
            f"[FCM] Multicast result: {success_count} succeeded, {failure_count} failed "
            f"(total={len(tokens)})"
        )

        for idx, resp in enumerate(response.responses):
            if not resp.success:
                token = tokens[idx]
                error = resp.exception
                error_type = type(error).__name__ if error else 'UnknownError'
                serial = device_map.get(token, token[:20])
                logger.error(
                    f"[FCM] Multicast failure for device '{serial}': {error_type} — {str(error)}"
                )
                if isinstance(error, messaging.UnregisteredError):
                    try:
                        from .models import Device as _Device
                        dev = _Device.objects.get(fcm_token=token)
                        dev.fcm_token = None
                        dev.save(update_fields=['fcm_token'])
                        logger.info(f"[FCM] Cleared stale FCM token for device '{serial}'.")
                    except Exception as db_err:
                        logger.error(f"[FCM] Could not clear stale token for '{serial}': {db_err}")

    except Exception as e:
        logger.error(
            f"[FCM] Unexpected error in multicast send to {len(tokens)} device(s): {str(e)}",
            exc_info=True,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_fcm_notification(
    device,
    message: str,
    title: str = "Counter Update",
    data: Optional[Dict[str, Any]] = None,
):
    """Send FCM notification to a single TV device.

    The blocking HTTP call is submitted to the module-level ThreadPoolExecutor
    (non-daemon threads) so that IIS process recycling does NOT interrupt the
    call mid-flight — the worker always logs a success or error result.

    Returns:
        bool: True if the send was submitted to the executor.
    """
    if not device:
        logger.warning("send_fcm_notification called with no device.")
        return False

    serial = getattr(device, 'serial_number', 'UNKNOWN')

    if not device.fcm_token:
        logger.warning(f"[FCM] Device '{serial}' has no FCM token — notification skipped.")
        return False

    if device.device_type != Device.DeviceType.TV:
        logger.debug(f"[FCM] Device '{serial}' is not a TV (type={device.device_type}) — skipping.")
        return False

    token_preview = device.fcm_token[:20] + "..." if len(device.fcm_token) > 20 else device.fcm_token
    logger.info(
        f"[FCM] Sending notification to TV '{serial}' | "
        f"title='{title}' | token='{token_preview}' (len={len(device.fcm_token)}) | "
        f"data={data}"
    )

    firebase_app = get_firebase_app()
    if not firebase_app:
        logger.error(f"[FCM] Firebase app is not initialized — cannot send to '{serial}'.")
        return False

    str_data = {k: str(v) for k, v in (data or {}).items()}
    message_obj = messaging.Message(
        notification=messaging.Notification(title=title, body=message),
        token=device.fcm_token,
        data=str_data,
    )

    logger.info(f"[FCM] Submitting send to executor (non-daemon thread) for '{serial}'.")
    _fcm_executor.submit(_do_send_single, serial, message_obj, firebase_app, device.id)
    return True


def send_fcm_notifications(
    devices: List,
    message: str,
    title: str = "Counter Update",
    data: Optional[Dict[str, Any]] = None,
):
    """Send FCM notifications to multiple TV devices via MulticastMessage.

    Uses messaging.send_each_for_multicast() — the same approach as the
    working reference implementation. The blocking HTTP call is submitted to
    the module-level ThreadPoolExecutor (non-daemon), so it always completes.

    Returns:
        dict: {'success_count': N, 'failure_count': 0} — optimistic count
              submitted. Check fcm.log for actual per-device results.
    """
    if not devices:
        logger.debug("[FCM] send_fcm_notifications called with empty device list.")
        return {'success_count': 0, 'failure_count': 0}

    # Filter to TV devices that have a valid FCM token
    valid_devices = [d for d in devices if d and d.fcm_token and d.device_type == Device.DeviceType.TV]
    skipped = len(devices) - len(valid_devices)
    if skipped:
        logger.debug(f"[FCM] Skipped {skipped} device(s) with no FCM token or non-TV type.")

    if not valid_devices:
        logger.warning("[FCM] No valid TV devices with FCM tokens found. Nothing sent.")
        return {'success_count': 0, 'failure_count': 0}

    firebase_app = get_firebase_app()
    if not firebase_app:
        logger.error(f"[FCM] Firebase app not initialized — cannot send to {len(valid_devices)} device(s).")
        return {'success_count': 0, 'failure_count': len(valid_devices)}

    tokens = [d.fcm_token for d in valid_devices]
    # Map token -> serial_number for readable error logs
    device_map = {d.fcm_token: d.serial_number for d in valid_devices}

    str_data = {k: str(v) for k, v in (data or {}).items()}

    # Build a MulticastMessage — same pattern as the reference implementation
    multicast_msg = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=message),
        data=str_data,
        tokens=tokens,
    )

    logger.info(
        f"[FCM] Submitting multicast to executor (non-daemon thread) "
        f"({len(tokens)} TV(s)) | title='{title}' | data={data}"
    )
    _fcm_executor.submit(_do_send_multicast, tokens, multicast_msg, firebase_app, device_map)
    return {'success_count': len(valid_devices), 'failure_count': 0}
