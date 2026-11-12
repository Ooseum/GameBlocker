// Bridge to the Python backend (pywebview exposes window.pywebview.api).
// When running in a plain browser (dev / screenshot test) there is no
// pywebview, so we fall back to an in-memory mock with the same shape.

const hasPywebview = () =>
  typeof window !== 'undefined' && window.pywebview && window.pywebview.api

// ---- mock backend for browser testing ----
const mock = (() => {
  let state = {
    locked: false,
    theme: 'Daylight',
    minEnrolled: 3,
    enrolledCount: 3,
    enrolledNames: ['Grandma', 'Dad', 'Girlfriend'],
    blocklist: [
      'RobloxPlayerBeta.exe', 'steam.exe', 'FortniteClient-Win64-Shipping.exe',
      'Overwatch.exe', 'EpicGamesLauncher.exe', 'Battle.net.exe',
      'LeagueClient.exe', 'RiotClientServices.exe', 'Minecraft.exe',
    ],
    settingsUnlocked: false,
    manageUnlocked: false,
  }
  const ok = (extra = {}) => ({ ok: true, state: { ...state }, ...extra })
  const manageAllowed = (code) => {
    if (state.enrolledNames.length < 3) return true
    if (state.manageUnlocked) return true
    if (code === '131214' || code === '141213') { state.manageUnlocked = true; return true }
    return false
  }
  return {
    get_state: async () => ({ ...state }),
    lock: async () => {
      if (state.enrolledCount < state.minEnrolled)
        return { ok: false, error: `Enroll at least ${state.minEnrolled} people before locking.` }
      state.locked = true; return ok()
    },
    try_unlock: async (code) => {
      if (code === '131214' || code === '141213') { state.locked = false; return ok() }
      return { ok: false, error: "That didn't match 3 different people." }
    },
    enroll: async (name, num) => {
      if (!/^\d{1,3}$/.test(num)) return { ok: false, error: 'Number must be 1-3 digits.' }
      state.enrolledCount += 1; state.enrolledNames.push(name || 'New'); return ok()
    },
    edit_number: async (i, code, num) => {
      if (!manageAllowed(code)) return { ok: false, needCode: true }
      if (!/^\d{1,3}$/.test(num)) return { ok: false, error: 'Number must be 1-3 digits.' }
      return ok()
    },
    remove_enrolled: async (i, code) => {
      if (!manageAllowed(code)) return { ok: false, needCode: true }
      state.enrolledNames.splice(i, 1); state.enrolledCount = state.enrolledNames.length; return ok()
    },
    can_edit: async () => !state.locked || state.settingsUnlocked,
    unlock_settings: async (code) => {
      if (code === '131214' || code === '141213') { state.settingsUnlocked = true; return { ok: true } }
      return { ok: false, error: 'Need the family code to edit while locked.' }
    },
    add_game: async (name) => {
      if (name && name.trim()) state.blocklist.push(name.trim()); return ok()
    },
    remove_game: async (i) => { state.blocklist.splice(i, 1); return ok() },
    scan: async () => ['AmongUs.exe', 'Valorant.exe', 'Terraria.exe'],
    set_theme: async (name) => { state.theme = name; return ok() },
    minimize: async () => {},
    close: async () => {},
    start_drag: async () => {},
  }
})()

// pywebview injects window.pywebview.api slightly after the page loads and
// fires 'pywebviewready'. Wait for it before the first call, or the initial
// getState() races ahead of the bridge and falls back to the mock demo data.
// Strategy: if window.pywebview ever appears we are in the app — poll until the
// api is ready and NEVER use the mock. Only fall back to the mock when there is
// no pywebview at all after a few seconds (a plain browser, for dev/screenshots).
const ready = new Promise((resolve) => {
  if (typeof window === 'undefined') return resolve()
  if (hasPywebview()) return resolve()
  window.addEventListener('pywebviewready', resolve, { once: true })
  let tries = 0
  const iv = setInterval(() => {
    if (hasPywebview()) { clearInterval(iv); resolve() }
    else if (++tries > 40 && !window.pywebview) { clearInterval(iv); resolve() }
  }, 100)
})

const call = (name) => async (...args) => {
  await ready
  if (hasPywebview()) return window.pywebview.api[name](...args)
  return mock[name](...args)
}

export const api = {
  getState: call('get_state'),
  lock: call('lock'),
  tryUnlock: call('try_unlock'),
  enroll: call('enroll'),
  editNumber: call('edit_number'),
  removeEnrolled: call('remove_enrolled'),
  canEdit: call('can_edit'),
  unlockSettings: call('unlock_settings'),
  addGame: call('add_game'),
  removeGame: call('remove_game'),
  scan: call('scan'),
  setTheme: call('set_theme'),
  minimize: call('minimize'),
  close: call('close'),
  startDrag: call('start_drag'),
}
