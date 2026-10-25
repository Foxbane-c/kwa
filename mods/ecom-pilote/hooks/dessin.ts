// Le dessin du panneau en SVG, dans la grammaire du Mod Kwa (kwa-activity) : cadres arrondis colorés, pastilles,
// flèches, animations courtes, thème clair et sombre. Fonction pure : la même vue donne le même SVG, donc le cadre qui
// le montre ne se recharge que quand les données changent.
import type { Attente, Jour, Ligne, Porte, Tache, Vue } from '../types'
import { joursAvant } from './pilotage'

export type Drawing = { source: string; width: number; height: number }

const W = 360
const C = {
  toi: '#22c55e', attente: '#6366f1', claude: '#f97316', portes: '#eab308',
  fait: '#10b981', retard: '#ef4444', gris: '#a1a1aa', taches: '#0ea5e9',
}

const esc = (t: string) => t.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const cut = (t: string, n: number) => { const c = [...t]; return c.length > n ? c.slice(0, n - 1).join('') + '…' : t }
const jj = (d: string) => `${d.slice(8)}/${d.slice(5, 7)}`
const eur = (n: number) => `${n.toFixed(2).replace('.', ',')} €`
const pulse = (attr: string, values: string, dur = 1.6) => `<animate attributeName="${attr}" values="${values}" dur="${dur}s" repeatCount="indefinite"/>`
const tick = (x: number, y: number, s = 1) => `<path d="M${x - 4 * s} ${y} l${3 * s} ${3 * s} l${5.5 * s} ${-6 * s}" class="tick"/>`

// Un cadre de section, comme une brique Kwa ouverte : numéro, titre en capitales, compteur à droite
function cadre(y: number, h: number, n: number, titre: string, couleur: string, compte: string): string {
  return `<rect x="10" y="${y}" width="${W - 20}" height="${h}" rx="16" class="frame" style="stroke:${couleur}" stroke-opacity=".7"/>` +
    `<rect x="10" y="${y}" width="${W - 20}" height="${h}" rx="16" fill="${couleur}" fill-opacity=".07"/>` +
    `<circle cx="32" cy="${y + 22}" r="11" fill="${couleur}"/><text x="32" y="${y + 26}" class="num" text-anchor="middle">${n}</text>` +
    `<text x="52" y="${y + 27}" class="bh" style="fill:${couleur}">${esc(titre)}</text>` +
    `<text x="${W - 24}" y="${y + 26}" class="meta" text-anchor="end">${esc(compte)}</text>`
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
    else if (e.statut === 'en_cours') out += `<circle cx="${x}" cy="${y}" r="17" fill="none" stroke="${C.claude}" stroke-width="2">${pulse('opacity', '.8;.1;.8', 2)}</circle>` +
      `<circle cx="${x}" cy="${y}" r="12" fill="${C.claude}"/><text x="${x}" y="${y + 4}" class="num" text-anchor="middle">${i + 1}</text>`
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

// Une tâche Todoist : une boîte, un rond creux, le titre, l'échéance à droite (rouge si dépassée)
function boiteTache(t: Tache, y: number, couleur: string, now: number): string {
  const n = t.echeance ? joursAvant(t.echeance, now) : null
  const meta = t.echeance ? (n! < 0 ? `retard ${-n!} j` : n === 0 ? 'aujourd’hui' : jj(t.echeance)) : t.priorite === 'p1' ? 'prioritaire' : ''
  const brut = t.titre.replace(/^Claude\s*:\s*/i, '')
  const titre = brut.charAt(0).toUpperCase() + brut.slice(1)
  return `<rect x="24" y="${y}" width="${W - 48}" height="38" rx="10" class="box" style="stroke:${couleur}" stroke-opacity=".55"/>` +
    `<circle cx="44" cy="${y + 19}" r="7" class="hollow" style="stroke:${couleur}"/>` +
    `<text x="60" y="${y + 24}" class="sn">${esc(cut(titre, 30))}</text>` +
    `<text x="${W - 36}" y="${y + 23}" class="meta${n !== null && n < 0 ? ' alerte' : ''}" text-anchor="end">${esc(meta)}</text>`
}

// Une attente : état à gauche, quoi et qui, compte à rebours en pastille, et la barre du temps écoulé
function boiteAttente(a: Attente, y: number, now: number): string {
  const reste = joursAvant(a.echeance, now)
  const total = Math.max(1, joursAvant(a.echeance, Date.parse(`${a.depuis}T12:00:00`)))
  const ecoule = a.etat === 'recu' ? 1 : Math.min(1, Math.max(0, (total - reste) / total))
  const retard = a.etat !== 'recu' && reste < 0
  const teinte = a.etat === 'recu' ? C.fait : retard ? C.retard : C.attente
  const pastille = a.etat === 'recu' ? 'reçu' : retard ? `+${-reste} j` : reste === 0 ? 'auj.' : `J-${reste}`
  const L = W - 48 - 24
  let icone = ''
  if (a.etat === 'recu') icone = `<circle cx="44" cy="${y + 20}" r="9" fill="${C.fait}"/>${tick(44, y + 20, 0.9)}`
  else if (a.etat === 'repondu') icone = `<circle cx="44" cy="${y + 20}" r="8" class="hollow" style="stroke:${teinte}"/><path d="M44 ${y + 12} A8 8 0 0 1 44 ${y + 28} Z" fill="${teinte}"/>`
  else icone = `<circle cx="44" cy="${y + 20}" r="6" fill="${teinte}"/><circle cx="44" cy="${y + 20}" r="6" fill="none" stroke="${teinte}" stroke-width="2">${pulse('r', '6;12', 1.8)}${pulse('opacity', '.8;0', 1.8)}</circle>`
  return `<rect x="24" y="${y}" width="${W - 48}" height="58" rx="10" class="box"${retard ? ` style="stroke:${C.retard}"` : ''}/>` + icone +
    `<text x="60" y="${y + 22}" class="sn">${esc(cut(a.quoi, 26))}</text>` +
    `<text x="60" y="${y + 38}" class="mini">${esc(cut(a.qui, 34))}</text>` +
    `<rect x="${W - 86}" y="${y + 9}" width="50" height="20" rx="10" fill="${teinte}" fill-opacity="${retard ? 1 : 0.15}"/>` +
    `<text x="${W - 61}" y="${y + 23}" class="pill${retard ? ' blanc' : ''}" style="${retard ? '' : `fill:${teinte}`}" text-anchor="middle">${esc(pastille)}</text>` +
    `<rect x="36" y="${y + 46}" width="${L}" height="4" rx="2" class="track"/>` +
    `<rect x="36" y="${y + 46}" width="${Math.max(4, L * ecoule)}" height="4" rx="2" fill="${teinte}" fill-opacity=".8"/>`
}

// Les portes : un anneau « n / total » et une pastille par critère, sur deux colonnes
function portes(liste: Porte[], y: number, intro: boolean): { svg: string; h: number } {
  const ok = liste.filter(p => p.statut === 'ok').length
  const R = 26, Cc = 2 * Math.PI * R, dash = liste.length ? (Cc * ok) / liste.length : 0
  let out = `<g transform="translate(52 ${y + 40}) rotate(-90)"><circle r="${R}" class="anneau" stroke-width="8"/>` +
    `<circle r="${R}" fill="none" stroke="${C.fait}" stroke-width="8" stroke-linecap="round" stroke-dasharray="${dash} ${Cc}">` +
    (intro ? `<animate attributeName="stroke-dasharray" from="0 ${Cc}" to="${dash} ${Cc}" dur="1s"/>` : '') + `</circle></g>` +
    `<text x="52" y="${y + 45}" class="pct" text-anchor="middle">${ok}/${liste.length}</text>`
  // une porte par ligne, à droite de l'anneau : le critère entier reste lisible
  const x0 = 96, larg = W - 24 - x0
  liste.forEach((p, i) => {
    const cy = y + 4 + i * 26
    const teinte = p.statut === 'ok' ? C.fait : p.statut === 'ko' ? C.retard : C.gris
    out += `<rect x="${x0}" y="${cy}" width="${larg}" height="20" rx="10" fill="${teinte}" fill-opacity="${p.statut === 'inconnu' ? 0.08 : 0.16}"${p.statut === 'inconnu' ? ` stroke="${teinte}" stroke-opacity=".5" stroke-dasharray="3 3"` : ''}/>` +
      `<text x="${x0 + 10}" y="${cy + 14}" class="porte"${p.statut === 'inconnu' ? '' : ` style="fill:${teinte}"`}>${p.statut === 'ok' ? '✓' : p.statut === 'ko' ? '✗' : '?'} ${esc(cut(p.critere, 24))}</text>` +
      (p.valeur ? `<text x="${x0 + larg - 10}" y="${cy + 14}" class="porte" text-anchor="end">${esc(cut(p.valeur, 16))}</text>` : '')
  })
  return { svg: out, h: Math.max(84, liste.length * 26 + 4) }
}

// `intro` : première apparition du panneau sur une surface ; la jauge et l'anneau se remplissent alors une seule fois.
// `partie` : « tete » (titre, parcours, budget) et « suite » (les quatre sections) encadrent le tableau des tâches
// sur desktop ; « tout » dessine les deux d'un bloc.
export function dessin(v: Vue, now: number, { intro = false, partie = 'tout' }: { intro?: boolean; partie?: 'tout' | 'tete' | 'suite' } = {}): Drawing {
  const s = v.etat!
  let y = 0
  let out = ''
  if (partie !== 'suite') {
    out += `<text x="16" y="28" class="title">Pilotage</text>` +
      `<text x="16" y="48" class="meta">${esc(cut(s.produit, 46))}</text>`
    out += parcours(v, 84)
    out += budget(v, 140, intro)
    y = 176
    if (partie === 'tete') return svg(out, 170)
  } else y = 8

  const sections: { n: number; titre: string; couleur: string; compte: string; corps: (y0: number) => { svg: string; h: number } }[] = [
    { n: 1, titre: 'À toi', couleur: C.toi, compte: `${v.aToi.length}`, corps: y0 => {
      if (!v.aToi.length) return { svg: `<text x="24" y="${y0 + 18}" class="meta">Rien ne t’attend. Profite.</text>`, h: 28 }
      return { svg: v.aToi.map((t, i) => boiteTache(t, y0 + i * 46, C.toi, now)).join(''), h: v.aToi.length * 46 - 8 }
    } },
    { n: 2, titre: 'J’attends', couleur: C.attente, compte: `${s.attentes.filter(a => a.etat !== 'recu').length} en cours`, corps: y0 => {
      const liste = [...s.attentes].sort((a, b) => (a.etat === 'recu' ? 1 : 0) - (b.etat === 'recu' ? 1 : 0) || a.echeance.localeCompare(b.echeance))
      if (!liste.length) return { svg: `<text x="24" y="${y0 + 18}" class="meta">Rien en attente.</text>`, h: 28 }
      return { svg: liste.map((a, i) => boiteAttente(a, y0 + i * 66, now)).join(''), h: liste.length * 66 - 8 }
    } },
    { n: 3, titre: 'Claude fait', couleur: C.claude, compte: `${v.claude.length}`, corps: y0 => {
      if (!v.claude.length) return { svg: `<text x="24" y="${y0 + 18}" class="meta">Rien de prévu.</text>`, h: 28 }
      return { svg: v.claude.map((t, i) => boiteTache(t, y0 + i * 46, C.claude, now)).join(''), h: v.claude.length * 46 - 8 }
    } },
    { n: 4, titre: 'Portes avant le lot', couleur: C.portes, compte: `${s.portes.filter(p => p.statut === 'ok').length} sur ${s.portes.length}`, corps: y0 => portes(s.portes, y0, intro) },
  ]
  let precedent = 0
  for (const sec of sections) {
    const corps = sec.corps(y + 46)
    const h = 46 + corps.h + 14
    if (precedent) out += `<line x1="${W / 2}" y1="${precedent}" x2="${W / 2}" y2="${y - 1}" class="lien on"/><path d="M${W / 2 - 5} ${y - 7} L${W / 2} ${y} L${W / 2 + 5} ${y - 7}" class="tip"/>`
    out += cadre(y, h, sec.n, sec.titre, sec.couleur, sec.compte) + corps.svg
    precedent = y + h
    y += h + 22
  }
  // l'heure de relecture est dessinée en texte natif sous le schéma : le SVG ne change ainsi qu'avec les données
  return svg(out, y - 8)
}

// L'en-tête du tableau des tâches : les trois compteurs, et qui tient la baguette
export function dessinTaches(liste: Jour[], memoire: number): Drawing {
  const n = (k: 'fait' | 'enCours' | 'enAttente') => liste.reduce((t, j) => t + j[k], 0)
  const encours = n('enCours')
  const pills: [string, number, string][] = [['Fait', n('fait'), C.fait], ['En cours', encours, C.claude], ['En attente', n('enAttente'), C.attente]]
  const L = (W - 40 - 16) / 3
  let out = `<text x="16" y="22" class="bh" style="fill:${C.taches}">Tâches</text>` +
    `<text x="${W - 16}" y="22" class="meta" text-anchor="end">pliables par jour</text>`
  pills.forEach(([nom, k, teinte], i) => {
    const x = 20 + i * (L + 8)
    out += `<rect x="${x}" y="34" width="${L}" height="44" rx="12" fill="${teinte}" fill-opacity=".12" stroke="${teinte}" stroke-opacity=".5"/>` +
      `<text x="${x + 12}" y="56" class="pct" style="fill:${teinte}">${k}</text>` +
      `<text x="${x + 12}" y="71" class="mini">${nom}</text>` +
      (nom === 'En cours' && k > 0 ? `<circle cx="${x + L - 14}" cy="50" r="5" fill="${teinte}"/><circle cx="${x + L - 14}" cy="50" r="5" fill="none" stroke="${teinte}" stroke-width="2">${pulse('r', '5;11', 1.4)}${pulse('opacity', '.9;0', 1.4)}</circle>` : '')
  })
  const chef = memoire > 0 ? `vault consulté ${memoire} fois aujourd’hui` : 'vault pas encore consulté aujourd’hui'
  out += `<circle cx="27" cy="97" r="6" fill="${memoire > 0 ? C.fait : C.gris}"/>` +
    `<text x="40" y="101" class="mini"><tspan class="fort">Chef d’orchestre : Claude</tspan> · ${chef}</text>`
  return svg(out, 112)
}

// Une ligne : l'état à gauche (coche, halo qui respire, rond creux), le titre, qui la porte, la pastille « savoir »
function ligne(l: Ligne, y: number): string {
  const teinte = l.etat === 'fait' ? C.fait : l.etat === 'en_cours' ? C.claude : l.retard ? C.retard : C.attente
  const H = 50
  let o = `<rect x="16" y="${y}" width="${W - 32}" height="${H}" rx="10" class="box"${l.etat === 'en_attente' && !l.retard ? '' : ` style="stroke:${teinte}"`} stroke-opacity="${l.etat === 'en_cours' ? 1 : 0.55}"/>`
  if (l.etat === 'en_cours')
    o += `<rect x="16" y="${y}" width="${W - 32}" height="${H}" rx="10" fill="none" stroke="${teinte}" stroke-width="2.2" stroke-dasharray="40 ${2 * (W - 32 + H) - 40}">` +
      `<animate attributeName="stroke-dashoffset" from="0" to="${-2 * (W - 32 + H)}" dur="3s" repeatCount="indefinite"/></rect>` +
      `<circle cx="36" cy="${y + H / 2}" r="7" fill="${teinte}"/><circle cx="36" cy="${y + H / 2}" r="7" fill="none" stroke="${teinte}" stroke-width="2">${pulse('r', '7;13', 1.4)}${pulse('opacity', '.9;0', 1.4)}</circle>`
  else if (l.etat === 'fait') o += `<circle cx="36" cy="${y + H / 2}" r="9" fill="${teinte}"/>${tick(36, y + H / 2, 0.9)}`
  else o += `<circle cx="36" cy="${y + H / 2}" r="7" class="hollow" style="stroke:${teinte}"/>`
  const titre = l.titre.charAt(0).toUpperCase() + l.titre.slice(1)
  const qui = [l.qui, l.agent, l.heure].filter(Boolean).join(' · ')
  o += `<text x="54" y="${y + 21}" class="sn${l.etat === 'fait' ? ' fini' : ''}">${esc(cut(titre, l.savoir === 'sans_objet' ? 34 : 27))}</text>` +
    `<text x="54" y="${y + 38}" class="mini${l.etat === 'en_cours' ? ' vif' : ''}">${esc(cut(l.retard ? `${qui} · en retard` : qui, 46))}</text>`
  if (l.savoir !== 'sans_objet') {
    const ok = l.savoir === 'oui'
    o += `<rect x="${W - 92}" y="${y + 8}" width="64" height="18" rx="9" fill="${ok ? C.fait : C.gris}" fill-opacity="${ok ? 0.16 : 0.1}"${ok ? '' : ` stroke="${C.gris}" stroke-opacity=".5" stroke-dasharray="3 3"`}/>` +
      `<text x="${W - 60}" y="${y + 21}" class="porte" style="fill:${ok ? C.fait : C.gris}" text-anchor="middle">${ok ? '✓ savoir' : '? savoir'}</text>`
  }
  return o
}

const MAX_LIGNES = 12

// Les tâches d'un jour déplié
export function dessinJour(j: Jour): Drawing {
  const vues = j.lignes.slice(0, MAX_LIGNES)
  let out = vues.map((l, i) => ligne(l, 4 + i * 56)).join('')
  let h = 4 + vues.length * 56
  if (j.lignes.length > vues.length) {
    out += `<text x="20" y="${h + 12}" class="meta">… et ${j.lignes.length - vues.length} autres</text>`
    h += 22
  }
  return svg(out, h)
}

const STYLE = `<style>
text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#18181b}
.title{font-size:20px;font-weight:750}.bh{font-size:13px;font-weight:750;letter-spacing:.06em;text-transform:uppercase}
.num{font-size:12px;font-weight:700;fill:#fff}.num.dim{fill:#71717a}.wl{font-size:11px;font-weight:600;fill:#71717a}.wl.on{font-weight:800;fill:${C.claude}}
.sn{font-size:13.5px;font-weight:550}.mini{font-size:11px;fill:#71717a}.meta{font-size:12px;fill:#71717a}.meta.alerte{fill:${C.retard};font-weight:700}.sn.fini{fill:#71717a}.mini.vif{fill:${C.claude};font-weight:650}
.fort{font-weight:750;fill:#18181b}.pill{font-size:11px;font-weight:750}.pill.blanc{fill:#fff}.pct{font-size:14px;font-weight:750}.porte{font-size:11px;font-weight:600;fill:#71717a}
.frame{fill:none;stroke-width:1.6}.box{fill:#ffffff;stroke:#d4d4d8;stroke-width:1.3}.hollow{fill:none;stroke:#a1a1aa;stroke-width:2}
.track{fill:#e4e4e7;stroke:#e4e4e7}.anneau{fill:none;stroke:#e4e4e7}.lien{stroke-width:2}.lien.on{stroke:${C.fait}}.lien.off{stroke:#d4d4d8;stroke-dasharray:3 4}
.tip{fill:none;stroke:${C.fait};stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.tick{fill:none;stroke:#fff;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
@media (prefers-color-scheme: dark){text{fill:#fafafa}.meta,.mini,.wl,.porte{fill:#a1a1aa}.num.dim{fill:#a1a1aa}.fort{fill:#fafafa}
.box{fill:#18181b;stroke:#3f3f46}.track{fill:#3f3f46;stroke:#3f3f46}.anneau{stroke:#3f3f46}.lien.off{stroke:#3f3f46}.hollow{stroke:#71717a}}
</style>`

const svg = (out: string, H: number): Drawing =>
  ({ width: W, height: H, source: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">${STYLE}${out}</svg>` })
