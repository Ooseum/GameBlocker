import React, { useEffect, useState, useCallback } from 'react'
import { api } from './api.js'
import Icon from './Icon.jsx'

const THEMES = ['Daylight', 'Midnight', 'Focus', 'Slate', 'Rose']
const THEME_DOT = {
  Daylight: '#2D6CDF', Midnight: '#2FBF71', Focus: '#7C5CDE',
  Slate: '#1D9E8A', Rose: '#D4537E',
}

export default function App() {
  const [state, setState] = useState(null)
  const [view, setView] = useState('home')
  const [modal, setModal] = useState(null)
  const [toasts, setToasts] = useState([])
  const [pulse, setPulse] = useState(false)
  const [manageUnlocked, setManageUnlocked] = useState(false)

  const applyTheme = (name) =>
    document.documentElement.setAttribute('data-theme', name || 'Daylight')

  const refresh = useCallback(async () => {
    const s = await api.getState()
    setState(s); applyTheme(s.theme); return s
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const toast = (msg, kind = 'ok') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((t) => [...t, { id, msg, kind }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2600)
  }

  // grey click burst at the pointer, on every button except the window controls
  const burst = (x, y) => {
    for (let i = 0; i < 12; i++) {
      const a = (Math.PI * 2 / 12) * i + (Math.random() - 0.5) * 0.4
      const dx = Math.cos(a), dy = Math.sin(a)
      const el = document.createElement('div')
      el.className = 'spark'
      el.style.left = x + 'px'; el.style.top = y + 'px'
      document.body.appendChild(el)
      const dist = 26 + Math.random() * 14, start = performance.now(), dur = 360
      const tick = (now) => {
        const p = Math.min(1, (now - start) / dur), e = 1 - Math.pow(1 - p, 2)
        el.style.transform = `translate(${dx * dist * e}px, ${dy * dist * e}px) scale(${1 - p})`
        el.style.opacity = String(1 - p)
        if (p < 1) requestAnimationFrame(tick); else el.remove()
      }
      requestAnimationFrame(tick)
    }
  }
  const onClickCapture = (e) => {
    const b = e.target.closest('button')
    if (b && !b.classList.contains('wb')) burst(e.clientX, e.clientY)
  }

  if (!state) return <div className="app" />

  const locked = state.locked
  const canLock = state.enrolledCount >= state.minEnrolled

  const doLock = async () => {
    const r = await api.lock()
    if (r.ok) { setPulse(true); setTimeout(() => setPulse(false), 500); await refresh(); toast('Games locked') }
    else toast(r.error || 'Could not lock', 'err')
  }
  const doUnlock = () => setModal({
    kind: 'prompt', title: 'Unlock games', mask: true,
    desc: 'Everyone types their number into one box, any order.',
    submit: async (code) => {
      const r = await api.tryUnlock(code); setModal(null)
      if (r.ok) { setPulse(true); setTimeout(() => setPulse(false), 500); await refresh(); toast('Unlocked') }
      else toast(r.error || 'Wrong code', 'err')
    },
  })
  const doEnroll = () => setModal({
    kind: 'prompt', title: 'Enroll a person', mask: false, placeholder: 'Name', desc: 'Who is this?',
    submit: (name) => {
      if (!name) { setModal(null); return }
      setModal({
        kind: 'prompt', title: `${name}'s number`, mask: true, placeholder: '1-3 digits',
        desc: `${name} types their favorite number. You won't see it again.`,
        submit: async (num) => {
          const r = await api.enroll(name, num); setModal(null)
          if (r.ok) { await refresh(); toast(`Enrolled ${name}`) }
          else toast(r.error || 'Could not enroll', 'err')
        },
      })
    },
  })
  const manageNeedsCode = () => state.enrolledCount >= state.minEnrolled && !manageUnlocked

  const editPerson = (i, name) => {
    if (manageNeedsCode()) {
      setModal({
        kind: 'edit', title: `Edit ${name}'s number`,
        submit: async (code, num) => {
          const r = await api.editNumber(i, code, num)
          if (r.ok) { setManageUnlocked(true); setModal(null); await refresh(); toast(`Updated ${name}`) }
          else if (r.needCode) toast("That didn't match 3 different people.", 'err')  // keep modal open to retry
          else { setModal(null); toast(r.error || 'Could not update', 'err') }
        },
      })
    } else {
      setModal({
        kind: 'prompt', title: `Edit ${name}'s number`, mask: true, placeholder: 'New number (1-3 digits)',
        desc: `Set ${name}'s new number.`,
        submit: async (num) => {
          const r = await api.editNumber(i, '', num); setModal(null)
          if (r.ok) { await refresh(); toast(`Updated ${name}`) }
          else toast(r.error || 'Could not update', 'err')
        },
      })
    }
  }

  const removePerson = (i, name) => {
    if (manageNeedsCode()) {
      setModal({
        kind: 'prompt', title: `Remove ${name}`, mask: true,
        desc: `Enter the family code to remove ${name}.`,
        submit: async (code) => {
          const r = await api.removeEnrolled(i, code)
          if (r.ok) { setManageUnlocked(true); setModal(null); await refresh(); toast(`Removed ${name}`) }
          else if (r.needCode) toast("That didn't match 3 different people.", 'err')  // keep modal open to retry
          else { setModal(null); toast(r.error || 'Could not remove', 'err') }
        },
      })
    } else {
      api.removeEnrolled(i, '').then(async (r) => {
        if (r.ok) { await refresh(); toast(`Removed ${name}`) }
        else toast(r.error || 'Could not remove', 'err')
      })
    }
  }

  const guardEdit = async () => {
    if (await api.canEdit()) return true
    return new Promise((resolve) => setModal({
      kind: 'prompt', title: 'Locked', mask: true,
      desc: 'Enter the family code to edit games while locked.',
      submit: async (code) => {
        const r = await api.unlockSettings(code); setModal(null)
        if (r.ok) resolve(true); else { toast(r.error || 'Wrong code', 'err'); resolve(false) }
      },
      cancel: () => { setModal(null); resolve(false) },
    }))
  }
  const addGame = async () => {
    if (!(await guardEdit())) return
    setModal({
      kind: 'prompt', title: 'Add game', mask: false, placeholder: 'AmongUs.exe', desc: 'Process name to block.',
      submit: async (name) => { setModal(null); if (name && name.trim()) { await api.addGame(name); await refresh(); toast('Added') } },
    })
  }
  const removeGame = async (i) => { if (!(await guardEdit())) return; await api.removeGame(i); await refresh() }
  const doScan = async () => {
    if (!(await guardEdit())) return
    const found = await api.scan()
    const existing = new Set(state.blocklist.map((g) => g.toLowerCase()))
    const fresh = found.filter((g) => !existing.has(g.toLowerCase()))
    if (!fresh.length) { toast('No new games found'); return }
    setModal({ kind: 'scan', title: 'Games found', items: fresh })
  }
  const changeTheme = async (name) => { await api.setTheme(name); applyTheme(name); setState((s) => ({ ...s, theme: name })) }

  const preview = state.blocklist.slice(0, 3).map((g) => g.replace('.exe', '')).join(', ') || 'none yet'

  return (
    <div className="app" onClickCapture={onClickCapture}>
      <div className="titlebar">
        <div className="drag pywebview-drag-region">
          <div className="logo"><Icon name="gamepad" size={15} /></div>
          <span className="title">Game Blocker</span>
        </div>
        <div className="winbtns">
          <button className="wb" aria-label="Minimize" onClick={() => api.minimize()}>
            <svg width="11" height="11" viewBox="0 0 11 11"><line x1="2" y1="6" x2="9" y2="6" stroke="currentColor" strokeWidth="1.3" /></svg>
          </button>
          <button className="wb close" aria-label="Close" onClick={() => api.close()}>
            <svg width="11" height="11" viewBox="0 0 11 11"><path d="M2 2l7 7M9 2l-7 7" stroke="currentColor" strokeWidth="1.3" /></svg>
          </button>
        </div>
      </div>

      <div className="body">
        {view === 'home' ? (
          <>
            <div className={`pill ${locked ? 'locked' : 'ok'} ${pulse ? 'pulse' : ''}`}>
              <Icon name={locked ? 'lock' : 'unlock'} size={14} />
              {locked ? 'Locked' : 'Unlocked'}
            </div>
            <div className="count">{state.blocklist.length} games blocked</div>
            <div className="preview">{preview}</div>

            {locked ? (
              <button className="btn primary" onClick={doUnlock}><Icon name="unlock" /> Unlock games</button>
            ) : (
              <button className={`btn primary${canLock ? '' : ' disabled'}`} onClick={doLock}><Icon name="lock" /> Lock games</button>
            )}

            <div className="row">
              <button className="btn sec" onClick={() => setView('manage')}><Icon name="user" size={16} /> Manage enrolled</button>
              <button className="btn sec" onClick={() => setView('settings')}><Icon name="gear" size={16} /> Settings</button>
            </div>
            <div className="hint">{state.enrolledCount} people enrolled{!canLock && ` · need ${state.minEnrolled} to lock`}</div>
          </>
        ) : view === 'manage' ? (
          <>
            <button className="back" onClick={() => setView('home')}><Icon name="back" size={15} /> Back</button>
            <div className="count" style={{ fontSize: 15 }}>Manage enrolled</div>
            <div className="preview" style={{ marginBottom: 10 }}>Editing a number needs the family code</div>
            <div className="list">
              {state.enrolledNames.length === 0 && (
                <div className="item" style={{ color: 'var(--muted)' }}>No one enrolled yet</div>
              )}
              {state.enrolledNames.map((nm, i) => (
                <div className="item" key={nm + i}>{nm}
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
                    <button className="rowbtn" onClick={() => editPerson(i, nm)} aria-label="Edit number"><Icon name="edit" size={13} /></button>
                    <button className="rowbtn" onClick={() => removePerson(i, nm)} aria-label="Remove"><Icon name="x" size={13} /></button>
                  </div>
                </div>
              ))}
            </div>
            <div className="row">
              <button className="btn sec" onClick={doEnroll}><Icon name="plus" size={16} /> Add person</button>
            </div>
          </>
        ) : (
          <>
            <button className="back" onClick={() => setView('home')}><Icon name="back" size={15} /> Back</button>
            <div className="label">Theme</div>
            <div className="theme-row">
              {THEMES.map((t) => (
                <button key={t} className={`swatch ${state.theme === t ? 'active' : ''}`} onClick={() => changeTheme(t)}>
                  <span className="dot" style={{ background: THEME_DOT[t] }} /> {t}
                </button>
              ))}
            </div>
            <div className="label">Blocked games</div>
            <div className="list">
              {state.blocklist.map((g, i) => (
                <div className="item" key={g + i}>{g}
                  <button className="x" onClick={() => removeGame(i)}><Icon name="x" size={13} /></button>
                </div>
              ))}
            </div>
            <div className="row">
              <button className="btn sec" onClick={addGame}><Icon name="plus" size={16} /> Add game</button>
              <button className="btn sec" onClick={doScan}><Icon name="search" size={16} /> Scan for games</button>
            </div>
          </>
        )}
      </div>

      {modal && <Modal key={modal.title} modal={modal} onClose={() => (modal.cancel ? modal.cancel() : setModal(null))}
        onScanAdd={async (items) => { for (const g of items) await api.addGame(g); setModal(null); await refresh(); toast(`Added ${items.length}`) }} />}

      <div className="toasts">
        {toasts.map((t) => (<div key={t.id} className={`toast ${t.kind}`}><span className="tdot" /> {t.msg}</div>))}
      </div>
    </div>
  )
}

function Modal({ modal, onClose, onScanAdd }) {
  const [val, setVal] = useState('')
  const [val2, setVal2] = useState('')
  const [checked, setChecked] = useState(modal.items ? new Set(modal.items) : null)

  if (modal.kind === 'edit') {
    return (
      <div className="overlay" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <h3>{modal.title}</h3>
          <p>Enter the family code first, then set the new number.</p>
          <input className="input" type="password" autoFocus placeholder="Everyone's numbers, any order"
            value={val} onChange={(e) => setVal(e.target.value)} style={{ marginBottom: 9 }} />
          <input className="input" type="password" placeholder="New number (1-3 digits)"
            value={val2} onChange={(e) => setVal2(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') modal.submit(val, val2); if (e.key === 'Escape') onClose() }} />
          <div className="modal-row">
            <button className="btn sec" onClick={onClose}>Cancel</button>
            <button className="btn primary" style={{ margin: 0 }} onClick={() => modal.submit(val, val2)}>Save</button>
          </div>
        </div>
      </div>
    )
  }

  if (modal.kind === 'scan') {
    const toggle = (g) => { const n = new Set(checked); n.has(g) ? n.delete(g) : n.add(g); setChecked(n) }
    return (
      <div className="overlay" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <h3>{modal.title}</h3><p>Check the ones to block.</p>
          <div className="list" style={{ maxHeight: 170, flex: 'none' }}>
            {modal.items.map((g) => (
              <label className="item" key={g} style={{ cursor: 'pointer' }}>
                <input type="checkbox" checked={checked.has(g)} onChange={() => toggle(g)} style={{ marginRight: 9 }} />{g}
              </label>
            ))}
          </div>
          <div className="modal-row">
            <button className="btn sec" onClick={onClose}>Cancel</button>
            <button className="btn primary" style={{ margin: 0 }} onClick={() => onScanAdd([...checked])}>Add selected</button>
          </div>
        </div>
      </div>
    )
  }
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{modal.title}</h3>{modal.desc && <p>{modal.desc}</p>}
        <input className="input" type={modal.mask ? 'password' : 'text'} autoFocus placeholder={modal.placeholder || ''}
          value={val} onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') modal.submit(val); if (e.key === 'Escape') onClose() }} />
        <div className="modal-row">
          <button className="btn sec" onClick={onClose}>Cancel</button>
          <button className="btn primary" style={{ margin: 0 }} onClick={() => modal.submit(val)}>OK</button>
        </div>
      </div>
    </div>
  )
}
