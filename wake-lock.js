/**
 * Screen Wake Lock API Manager
 *
 * Keeps the device screen awake while the dashboard is open using the
 * Screen Wake Lock API (navigator.wakeLock.request('screen')).
 *
 * Automatically reacquires the lock when the page becomes visible again
 * (after tab switch / minimize) or if the lock is released by the browser.
 *
 * Falls back to a lightweight keep-alive interval on browsers that don't
 * support the Wake Lock API. Note: the fallback cannot truly prevent screen
 * sleep — it only prevents aggressive JS timer throttling on hidden tabs.
 *
 * Initialises automatically when this script loads. Does not depend on any
 * framework or other scripts in the project.
 */

;(function () {
  'use strict'

  /* ------------------------------------------------------------------ */
  /*  Configuration                                                      */
  /* ------------------------------------------------------------------ */

  var CONFIG = {
    // How often the fallback "ping" runs (ms). Only used when Wake Lock
    // API is unsupported. Higher values = less CPU impact.
    FALLBACK_INTERVAL_MS: 20000,

    // Delay before trying to re-acquire the wake lock after a visibility
    // change (ms). Gives the browser time to settle.
    REACQUIRE_DELAY_MS: 1000,
  }

  /* ------------------------------------------------------------------ */
  /*  State                                                              */
  /* ------------------------------------------------------------------ */

  var wakeLock = null               // Active WakeLockSentinel instance
  var fallbackTimerId = null        // setInterval ID for fallback
  var isSupported = 'wakeLock' in navigator

  /* ------------------------------------------------------------------ */
  /*  Wake Lock — acquire / release                                      */
  /* ------------------------------------------------------------------ */

  /**
   * Request the screen wake lock. Logs success / failure to the console.
   * Automatically listens for the "release" event so we can re-acquire.
   */
  function acquireWakeLock() {
    // Guard: don't re-request if we already hold a lock
    if (wakeLock !== null) return

    navigator.wakeLock.request('screen').then(
      function (sentinel) {
        wakeLock = sentinel
        console.log('[WakeLock] Screen wake lock acquired')

        // When the browser releases the lock (e.g. low battery, page
        // loses focus), re-acquire automatically.
        sentinel.addEventListener('release', function () {
          wakeLock = null
          console.log('[WakeLock] Screen wake lock released (sentinel)')
          // Attempt to re-acquire immediately
          acquireWakeLock()
        })
      },
      function (err) {
        wakeLock = null
        console.log('[WakeLock] Failed to acquire screen wake lock:', err.name, err.message)
      }
    )
  }

  /**
   * Manually release the wake lock if one is held. Idempotent.
   */
  function releaseWakeLock() {
    if (wakeLock !== null) {
      var sentinel = wakeLock
      wakeLock = null
      sentinel.release().then(
        function () {
          console.log('[WakeLock] Screen wake lock released (manual)')
        },
        function () {
          console.log('[WakeLock] Screen wake lock release failed')
        }
      )
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Visibility change handler                                          */
  /* ------------------------------------------------------------------ */

  /**
   * When the page becomes visible again after being hidden, re-request
   * the wake lock. The small delay prevents rapid acquire/release cycles.
   */
  function handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
      console.log('[WakeLock] Page visible — re-acquiring wake lock')
      setTimeout(acquireWakeLock, CONFIG.REACQUIRE_DELAY_MS)
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Fallback — for browsers without Wake Lock API                      */
  /* ------------------------------------------------------------------ */

  /**
   * Start a lightweight periodic timer that keeps the JS event loop
   * minimally active. This does NOT prevent screen sleep — no software
   * fallback can. It only stops the browser from aggressively throttling
   * timers while the page is backgrounded.
   */
  function startFallback() {
    if (fallbackTimerId !== null) return

    console.log('[WakeLock] Wake Lock API not supported — using fallback keep-alive timer')

    fallbackTimerId = setInterval(function () {
      /* No-op: just keeping the timer slot warm */
    }, CONFIG.FALLBACK_INTERVAL_MS)
  }

  /**
   * Stop the fallback timer.
   */
  function stopFallback() {
    if (fallbackTimerId !== null) {
      clearInterval(fallbackTimerId)
      fallbackTimerId = null
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Initialisation                                                     */
  /* ------------------------------------------------------------------ */

  function init() {
    if (isSupported) {
      console.log('[WakeLock] Wake Lock API is supported')

      // Acquire the lock on page load
      acquireWakeLock()

      // Re-acquire when the page becomes visible (tab switch / minimise)
      document.addEventListener('visibilitychange', handleVisibilityChange)
    } else {
      startFallback()
    }

    // When the page unloads, clean up to avoid dangling references
    window.addEventListener('beforeunload', function () {
      releaseWakeLock()
      stopFallback()
    })
  }

  // Go
  init()
})()
