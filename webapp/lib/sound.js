"use client";
// A short two-note chime made with the Web Audio API (no audio file needed). Browsers only allow sound after the person has
// clicked or typed once, so the audio context is unlocked on the first interaction.
let ctx = null;
const KEY = "cos_sound";
export const soundOn = () => { try { return localStorage.getItem(KEY) !== "off"; } catch { return true; } };
export const setSound = (on) => { try { localStorage.setItem(KEY, on ? "on" : "off"); } catch {} };

function audio() {
  if (!ctx) { const C = window.AudioContext || window.webkitAudioContext; if (C) ctx = new C(); }
  return ctx;
}
export function unlockAudio() {
  const unlock = () => { const a = audio(); if (a && a.state === "suspended") a.resume(); };
  ["pointerdown", "keydown", "touchstart"].forEach((e) => window.addEventListener(e, unlock, { once: false, passive: true }));
}
export function playChime(kind = "alert") {
  if (typeof window === "undefined" || !soundOn()) return;
  window.__soundCount = (window.__soundCount || 0) + 1;          // lets automated tests confirm a sound was triggered
  const a = audio();
  if (!a || a.state !== "running") return;
  const notes = kind === "soft" ? [[660, 0, 0.12]] : [[880, 0, 0.14], [1175, 0.13, 0.22]];
  const t0 = a.currentTime;
  for (const [f, at, dur] of notes) {
    const o = a.createOscillator(), g = a.createGain();
    o.type = "sine"; o.frequency.value = f;
    g.gain.setValueAtTime(0.0001, t0 + at); g.gain.exponentialRampToValueAtTime(kind === "soft" ? 0.05 : 0.12, t0 + at + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t0 + at + dur);
    o.connect(g).connect(a.destination); o.start(t0 + at); o.stop(t0 + at + dur + 0.02);
  }
}
