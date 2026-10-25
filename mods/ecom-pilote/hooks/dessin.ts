// Le dessin du panneau en SVG, dans la grammaire du Mod Kwa (kwa-activity) : cartes arrondies colorées, pastilles,
// animations courtes, thème clair et sombre. Fonctions pures : la même vue donne le même SVG, donc le cadre qui le
// montre ne se recharge que quand les données changent.
import type { Carte, Section, Vue } from '../types'
import { joursAvant } from './pilotage'

export type Drawing = { source: string; width: number; height: number }

const W = 360
export const C = {
  en_cours: '#f97316', a_faire: '#0ea5e9', en_attente: '#6366f1', fait: '#10b981', retard: '#ef4444', gris: '#a1a1aa',
}

const esc = (t: string) => t.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const cut = (t: string, n: number) => { const c = [...t]; return c.length > n ? c.slice(0, n - 1).join('') + '…' : t }
const jj = (d: string) => `${d.slice(8)}/${d.slice(5, 7)}`
const eur = (n: number) => `${n.toFixed(2).replace('.', ',')} €`
const pulse = (attr: string, values: string, dur = 1.6) => `<animate attributeName="${attr}" values="${values}" dur="${dur}s" repeatCount="indefinite"/>`
const tick = (x: number, y: number, s = 1) => `<path d="M${x - 4 * s} ${y} l${3 * s} ${3 * s} l${5.5 * s} ${-6 * s}" class="tick"/>`

// Coupe un texte en lignes d'au plus n caractères, au mot ; la dernière ligne gardée finit par « … » si le texte déborde
export function lignes(t: string, n: number, max: number): string[] {
  const out: string[] = []
  let cur = ''
  for (const mot of t.split(/\s+/).filter(Boolean)) {
    if (!cur) cur = mot
    else if ([...cur].length + 1 + [...mot].length <= n) cur += ` ${mot}`
    else { out.push(cur); cur = mot }
  }
  if (cur) out.push(cur)
  if (out.length <= max) return out
  const garde = out.slice(0, max)
  const der = garde[max - 1]!
  garde[max - 1] = [...der].length < n ? `${der}…` : cut(der, n)
  return garde
}

// Le parcours du produit : des ronds reliés, celui en cours qui respire
function parcours(v: Vue, y: number): string {
  const etapes = v.etat!.etapes
  const n = etapes.length
  const pas = (W - 60) / Math.max(1, n - 1)
  let out = ''
  etapes.forEach((e, i) => {
    const x = 30 + i * pas
    if (i > 0) {
      const fait = etapes[i - 1]!.statut === 'fait'
      out += `<line x1="${x - pas + 15}" y1="${y}" x2="${x - 15}" y2="${y}" class="lien ${fait ? 'on' : 'off'}"/>`
    }
    if (e.statut === 'fait') out += `<circle cx="${x}" cy="${y}" r="12" fill="${C.fait}"/>${tick(x, y)}`
    else if (e.statut === 'en_cours') out += `<circle cx="${x}" cy="${y}" r="17" fill="none" stroke="${C.en_cours}" stroke-width="2">${pulse('opacity', '.8;.1;.8', 2)}</circle>` +
      `<circle cx="${x}" cy="${y}" r="12" fill="${C.en_cours}"/><text x="${x}" y="${y + 4}" class="num" text-anchor="middle">${i + 1}</text>`
    else out += `<circle cx="${x}" cy="${y}" r="11" class="hollow"/><text x="${x}" y="${y + 4}" class="num dim" text-anchor="middle">${i + 1}</text>`
    out += `<text x="${x}" y="${y + 32}" class="wl${e.statut === 'en_cours' ? ' on' : ''}" text-anchor="middle">${esc(cut(e.nom, 12))}</text>`
  })
  return out
}

// Le budget du lot : une jauge horizontale, orange passé 70 %, rouge passé 90 %
function budget(v: Vue, y: number, intro: boolean): string {
  const { depense, plafond } = v.etat!.budget
  const p = plafond > 0 ? Math.min(1, depense / plafond) : 0
  const teinte = p < 0.7 ? C.fait : p < 0.9 ? '#f59e0b' : C.retard
  const L = W - 40
  return `<text x="20" y="${y}" class="meta">Budget du lot</text>` +
    `<text x="${W - 20}" y="${y}" class="meta" text-anchor="end"><tspan class="fort">${eur(depense)}</tspan> / ${eur(plafond)}</text>` +
    `<rect x="20" y="${y + 8}" width="${L}" height="8" rx="4" class="track"/>` +
    `<rect x="20" y="${y + 8}" width="${Math.max(8, L * p)}" height="8" rx="4" fill="${teinte}">` +
    (intro ? `<animate attributeName="width" from="0" to="${Math.max(8, L * p)}" dur=".9s" fill="freeze"/>` : '') + `</rect>`
}

// L'en-tête : titre, parcours, budget, et qui tient la baguette (Claude, avec le nombre de relectures du vault)
export function dessinTete(v: Vue, memoire: number, intro: boolean): Drawing {
  const s = v.etat!
  const chef = memoire > 0 ? `mémoire du projet relue ${memoire} fois aujourd’hui` : 'mémoire du projet pas encore relue aujourd’hui'
  const out = `<text x="16" y="28" class="title">Pilotage</text>` +
    `<text x="16" y="48" class="meta">${esc(cut(s.produit, 46))}</text>` +
    parcours(v, 84) + budget(v, 140, intro) +
    `<circle cx="22" cy="187" r="5" fill="${memoire > 0 ? C.fait : C.gris}"/>` +
    `<text x="34" y="191" class="mini"><tspan class="fort">Chef d’orchestre : Claude</tspan> · ${chef}</text>`
  return svg(out, 200)
}

// La ligne du bas d'une carte : qui la porte et la date, dite selon la section
function meta(c: Carte, now: number): { texte: string; retard: boolean } {
  const qui = [c.qui, c.agent].filter(Boolean).join(' · ')
  if (!c.quand) return { texte: qui, retard: false }
  const n = joursAvant(c.quand, now)
  if (c.etat === 'fait') return { texte: `${qui} · ${n === 0 ? 'aujourd’hui' : n === -1 ? 'hier' : `le ${jj(c.quand)}`}`, retard: false }
  const quand = n < 0 ? `en retard de ${-n} j` : n === 0 ? 'aujourd’hui' : `J-${n} · ${jj(c.quand)}`
  return { texte: `${qui} · ${c.etat === 'en_attente' ? 'attendu ' : 'pour '}${quand}`, retard: n < 0 }
}

const T_TITRE = 34, T_RECIT = 46

// Une carte : l'icône d'état à gauche, le titre, le récit humain de ce qu'on a fait, et la ligne qui / quand
function carte(c: Carte, y: number, now: number, intro: boolean): { svg: string; h: number } {
  const titre = lignes(c.titre.charAt(0).toUpperCase() + c.titre.slice(1), T_TITRE, 2)
  const recit = lignes(c.recit, T_RECIT, 4)
  const m = meta(c, now)
  const teinte = m.retard ? C.retard : C[c.etat]
  const h = 14 + titre.length * 18 + recit.length * 16 + 26
  const fait = c.etat === 'fait'
  let o = `<rect x="14" y="${y}" width="${W - 28}" height="${h}" rx="12" class="box${fait ? ' finie' : ''}" style="stroke:${teinte}" stroke-opacity="${c.etat === 'en_cours' ? 0.9 : fait ? 0.3 : 0.55}"/>`
  const cy = y + 22
  if (c.etat === 'en_cours') {
    const per = 2 * (W - 28 + h)
    o += `<rect x="14" y="${y}" width="${W - 28}" height="${h}" rx="12" fill="none" stroke="${teinte}" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="46 ${per - 46}">` +
      `<animate attributeName="stroke-dashoffset" from="0" to="${-per}" dur="3.2s" repeatCount="indefinite"/></rect>` +
      `<circle cx="34" cy="${cy}" r="7" fill="${teinte}"/><circle cx="34" cy="${cy}" r="7" fill="none" stroke="${teinte}" stroke-width="2">${pulse('r', '7;14', 1.4)}${pulse('opacity', '.9;0', 1.4)}</circle>`
  } else if (c.etat === 'en_attente') {
    o += `<circle cx="34" cy="${cy}" r="8" fill="none" stroke="${teinte}" stroke-opacity=".3" stroke-width="2.4"/>` +
      `<path d="M34 ${cy - 8} A8 8 0 0 1 42 ${cy}" fill="none" stroke="${teinte}" stroke-width="2.4" stroke-linecap="round">` +
      `<animateTransform attributeName="transform" type="rotate" from="0 34 ${cy}" to="360 34 ${cy}" dur="2.4s" repeatCount="indefinite"/></path>`
  } else if (fait) o += `<circle cx="34" cy="${cy}" r="9" fill="${teinte}"/>${tick(34, cy, 0.9)}`
  else o += `<circle cx="34" cy="${cy}" r="8" fill="none" stroke="${teinte}" stroke-width="2"/>`

  let ty = y + 27
  titre.forEach(l => {
    o += `<text x="54" y="${ty}" class="sn${fait ? ' fini' : ''}">${esc(l)}</text>`
    if (fait) {
      const L = Math.min(W - 82, [...l].length * 7.3)
      o += `<line x1="54" y1="${ty - 4.5}" x2="${54 + L}" y2="${ty - 4.5}" class="barre" stroke-dasharray="${L}" stroke-dashoffset="0">` +
        (intro ? `<animate attributeName="stroke-dashoffset" from="${L}" to="0" dur=".7s" fill="freeze"/>` : '') + `</line>`
    }
    ty += 18
  })
  recit.forEach(l => { o += `<text x="54" y="${ty}" class="recit${fait ? ' fini' : ''}">${esc(l)}</text>`; ty += 16 })
  o += `<text x="54" y="${ty + 6}" class="mini${c.etat === 'en_cours' ? ' vif' : m.retard ? ' alerte' : ''}">${esc(cut(m.texte, 52))}</text>`
  return { svg: o, h }
}

// Les cartes d'une section dépliée, empilées
export function dessinSection(cartes: Carte[], section: Section, now: number, intro: boolean): Drawing {
  if (!cartes.length) {
    const vide = section === 'en_cours' ? 'Rien ne tourne en ce moment.' : section === 'en_attente' ? 'Rien en attente.' : section === 'a_faire' ? 'Rien à faire : bravo.' : 'Rien de fini pour l’instant.'
    return svg(`<text x="20" y="18" class="meta">${vide}</text>`, 28)
  }
  let y = 4, out = ''
  for (const c of cartes) {
    const k = carte(c, y, now, intro)
    out += k.svg
    y += k.h + 10
  }
  return svg(out, y)
}

const STYLE = `<style>
text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#18181b}
.title{font-size:20px;font-weight:750}
.num{font-size:12px;font-weight:700;fill:#fff}.num.dim{fill:#71717a}.wl{font-size:11px;font-weight:600;fill:#71717a}.wl.on{font-weight:800;fill:${C.en_cours}}
.sn{font-size:13.5px;font-weight:650}.recit{font-size:12px;fill:#52525b}.mini{font-size:11px;fill:#71717a}.meta{font-size:12px;fill:#71717a}
.sn.fini,.recit.fini{fill:#a1a1aa}.mini.vif{fill:${C.en_cours};font-weight:650}.mini.alerte{fill:${C.retard};font-weight:700}
.fort{font-weight:750;fill:#18181b}
.box{fill:#ffffff;stroke-width:1.3}.box.finie{fill:#fafafa}.hollow{fill:none;stroke:#a1a1aa;stroke-width:2}.barre{stroke:#a1a1aa;stroke-width:1.4;stroke-linecap:round}
.track{fill:#e4e4e7;stroke:#e4e4e7}.lien{stroke-width:2}.lien.on{stroke:${C.fait}}.lien.off{stroke:#d4d4d8;stroke-dasharray:3 4}
.tick{fill:none;stroke:#fff;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
@media (prefers-color-scheme: dark){text{fill:#fafafa}.meta,.mini,.wl{fill:#a1a1aa}.recit{fill:#d4d4d8}.num.dim{fill:#a1a1aa}.fort{fill:#fafafa}
.sn.fini,.recit.fini{fill:#71717a}.barre{stroke:#71717a}
.box{fill:#18181b}.box.finie{fill:#141416}.track{fill:#3f3f46;stroke:#3f3f46}.lien.off{stroke:#3f3f46}.hollow{stroke:#71717a}}
</style>`

const svg = (out: string, H: number): Drawing =>
  ({ width: W, height: H, source: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${STYLE}${out}</svg>` })
