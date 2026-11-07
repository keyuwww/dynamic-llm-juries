#!/usr/bin/env python3
"""Build results/gap_report.html: one plain-language story with charts (self-contained, inline SVG, light + dark).

Reads results/gap_summary.json (the gap check), step1_test.json (run-time nudge), step2_final.json and
step2_ablate_dev.json (permanent weight edit). Headline "knows vs says" numbers are the fair ones: 5-fold CV,
scored only within answers from the same source, so the detector can't win by spotting who wrote the answer.

  .venv/bin/python experiments/weight_space/build_report.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Judge Knows vs Says</title>
<style>
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;
--axis:#c3c2b7;--ring:rgba(11,11,11,.10);--says:#eb6834;--knows:#2a78d6;--short:#898781;--chip:#f0efec;--good:#006300;--bad:#d03b3b}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;
--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);
--says:#d95926;--knows:#3987e5;--short:#898781;--chip:#262624;--good:#0ca30c;--bad:#e66767}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;
--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--says:#d95926;--knows:#3987e5;--short:#898781;--chip:#262624;
--good:#0ca30c;--bad:#e66767}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
main{max-width:980px;margin:0 auto;padding:40px 16px 80px}
h1{font-size:34px;line-height:1.15;margin:0 0 10px;letter-spacing:-.01em}
h2{font-size:23px;margin:0 0 4px}h3{font-size:16px;margin:0 0 2px}
.kicker{font-size:12.5px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:52px 0 6px}
.lead{font-size:18px;color:var(--ink2);max-width:780px;margin:0}
.sec-lead{font-size:16px;color:var(--ink2);max-width:780px;margin:4px 0 14px}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:14px;padding:18px;position:relative}
.grid{display:grid;gap:14px}.g3{grid-template-columns:repeat(auto-fit,minmax(250px,1fr))}.g2{grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}
.hero{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin-top:26px}
.hero .card{padding:16px 18px}.hero .lbl{font-size:13px;color:var(--ink2);font-weight:600}
.hero .big{font-size:32px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.2;margin:4px 0 2px}
.hero .sub{font-size:13.5px;color:var(--ink2)}
.arrow{color:var(--muted);font-weight:400;margin:0 4px}
.answer{margin-top:22px;padding:16px 18px;border-left:4px solid var(--knows);background:var(--surface);border-radius:0 12px 12px 0;font-size:17px}
.step{display:flex;flex-direction:column;gap:6px}.step .n{font-size:12px;font-weight:700;letter-spacing:.06em;color:var(--muted)}
.step .what{font-size:14.5px;color:var(--ink2)}.step .res{font-size:14.5px;padding-top:8px;border-top:1px solid var(--grid);margin-top:auto}
.split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:22px;align-items:center}
@media (max-width:780px){.split{grid-template-columns:1fr}}
.takeaway{font-size:15.5px}.takeaway ul{margin:6px 0 0;padding-left:20px}.takeaway li{margin:5px 0}
.mean{margin-top:12px;padding:10px 14px;border-radius:10px;background:var(--chip);font-size:15px}
.mean b{color:var(--ink)}
.num{font-variant-numeric:tabular-nums;font-weight:700}
.chip{display:inline-block;font-size:12.5px;font-weight:600;padding:2px 10px;border-radius:999px;background:var(--chip);color:var(--ink);vertical-align:2px;margin-left:6px}
.yes{color:var(--good);font-weight:700}.no{color:var(--bad);font-weight:700}.meh{color:var(--muted);font-weight:700}
svg{display:block;width:100%;height:auto;overflow:visible}
svg text{fill:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
svg .lab{fill:var(--ink);font-size:13.5px;font-weight:600}svg .lab2{fill:var(--ink2);font-size:12px}
svg .ann{fill:var(--ink2);font-size:12px}svg .val{fill:var(--ink);font-size:12.5px;font-weight:700}
.legend{display:flex;flex-wrap:wrap;gap:16px;font-size:13.5px;color:var(--ink2);margin-top:10px}
.dot{width:12px;height:12px;border-radius:50%;display:inline-block;vertical-align:-1px;margin-right:6px}
.ring{width:12px;height:12px;border-radius:50%;border:2px solid var(--short);display:inline-block;vertical-align:-1px;margin-right:6px}
.why{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
table.check{border-collapse:collapse;width:100%;font-size:14.5px}
table.check th,table.check td{text-align:left;padding:10px 10px;border-bottom:1px solid var(--grid);vertical-align:top}
table.check th{font-size:12.5px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.05em}
.gen{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;line-height:1.5;word-break:break-word;color:var(--ink2)}
.tip{position:absolute;pointer-events:none;background:var(--surface);color:var(--ink);border:1px solid var(--ring);border-radius:8px;
padding:6px 9px;font-size:12.5px;box-shadow:0 4px 14px rgba(0,0,0,.14);display:none;white-space:nowrap;z-index:5}
details{margin-top:48px}summary{cursor:pointer;color:var(--ink2);font-size:15px}
.small{font-size:13.5px}.muted{color:var(--muted)}
table.det{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums;margin-top:10px}
table.det th,table.det td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid);vertical-align:top}table.det th{color:var(--ink2);font-weight:500}
.wrap{overflow-x:auto}
</style></head><body><main>

<h1>Does a small AI judge know more than it says?</h1>
<p class="lead">We asked a small model (Qwen3.5-0.8B) to grade answers as <b>good</b> or <b>bad</b>. Then we looked inside it to see whether it had worked out the right call but didn't say it, and whether a small change to its weights could make it say it.</p>

<div class="hero" id="hero"></div>
<div class="answer"><b>Short answer:</b> On <b>safety</b>, yes. The judge already knows which answers are fine but doesn't say so, and connecting that knowledge to its answer fixes it. On <b>finance</b> and <b>hard questions</b>, there's little hidden knowledge to use. And our permanent fix, as built so far, is <b>too blunt</b>: it also scrambles other tasks.</div>

<!-- ===================================================== THE IDEA -->
<div class="kicker">The idea</div>
<h2>"Knowing" and "saying" can come apart</h2>
<p class="sec-lead">A model works in layers. Somewhere in the middle it may work out that an answer is good, and that knowledge still has to reach the word it outputs. If nothing connects the two, the verdict ignores what the model knows.</p>
<div class="card" id="diagram"></div>

<!-- ===================================================== WHAT WE RAN -->
<div class="kicker">What we ran</div>
<h2>Three experiments, each building on the last</h2>
<p class="sec-lead">All three ran on a laptop at no cost. Every score below is on held-out items, never used for fitting or tuning.</p>
<div class="grid g3" id="steps"></div>

<!-- ===================================================== RESULT 1 -->
<div class="kicker">Result 1 · The check</div>
<h2>It knows the answer on safety, but not on finance or hard questions</h2>
<p class="sec-lead">The longer the line, the more the judge knows but doesn't say. Scores run from <b>0.5 (coin flip)</b> to <b>1.0 (perfect)</b>, comparing only answers from the same source so cheap clues like "this source is usually wrong" can't inflate the result.</p>
<div class="card" id="dumbbell"></div>
<div class="legend"><span><span class="dot" style="background:var(--says)"></span>What it says (its verdict)</span><span><span class="dot" style="background:var(--knows)"></span>What it knows (read from inside)</span><span><span class="ring"></span>Cheap clues alone (length, source)</span></div>
<div class="grid g3" style="margin-top:14px" id="topics"></div>

<!-- ===================================================== RESULT 2 -->
<div class="kicker">Result 2 · Connect it while it runs</div>
<h2>Feeding the judge its own knowledge fixes the safety verdict</h2>
<div class="split" style="margin-top:12px">
  <div class="takeaway">
    <p><b>What we did:</b> while the judge reads each answer, we took its middle-layer "this looks fine / not fine" signal and used it to push its final word toward good or bad. No weights were changed.</p>
    <ul>
      <li>Score went <span class="num" id="r2_b"></span> → <span class="num" id="r2_a"></span>, as good as reading its insides directly.</li>
      <li>It now says "good" <span class="num" id="r2_sa"></span> of the time instead of <span class="num" id="r2_sb"></span>.</li>
      <li><b>Control:</b> pushing <i>every</i> answer toward "good" didn't help (<span class="num" id="r2_c"></span>). The gain comes from the knowledge, not from making it more positive.</li>
    </ul>
    <div class="mean"><b>What it means:</b> the knowledge is real and usable. The only thing missing is a link from "knows" to "says".</div>
  </div>
  <div class="card" id="r2chart"></div>
</div>

<!-- ===================================================== RESULT 3 -->
<div class="kicker">Result 3 · Build it into the weights</div>
<h2>A tiny permanent edit fixes safety, but breaks other things</h2>
<div class="split" style="margin-top:12px">
  <div class="takeaway">
    <p><b>What we did:</b> we built that link into the model itself by changing the output weights of <span class="num" id="r3_n"></span> neurons in one layer: <span class="num" id="r3_frac"></span> of the model.</p>
    <ul>
      <li><span class="yes">✓</span> <b>Safety:</b> <span class="num" id="r3_rb_b"></span> → <span class="num" id="r3_rb_a"></span>.</li>
      <li><span class="no">✗</span> <b>Finance:</b> <span class="num" id="r3_bff_b"></span> → <span class="num" id="r3_bff_a"></span>. It now calls almost every finance answer wrong.</li>
      <li><span class="no">✗</span> <b>Normal writing:</b> ordinary answers fill up with "INC INC INC…" (below).</li>
      <li><span class="meh">–</span> <b>The article's other trick</b> (deleting a direction) found nothing to delete. Switching off any later part never lifted safety above <span class="num" id="r3_abl"></span>.</li>
    </ul>
    <div class="mean"><b>What it means:</b> a small weight change <i>can</i> connect the knowledge, but ours is switched on for every word of every prompt. It needs to fire only when the model is giving a safety verdict.</div>
  </div>
  <div class="card" id="r3chart"></div>
</div>
<div class="grid g2" style="margin-top:14px" id="gen"></div>

<!-- ===================================================== WHY -->
<div class="kicker">Why only safety?</div>
<h2>You can only connect knowledge that's already there</h2>
<div class="card" style="margin-top:12px">
<div class="wrap"><table class="check" style="min-width:560px">
<tr><th>Topic</th><th>Does it have the knowledge?</th><th>Why</th><th>Can a fix help?</th></tr>
<tr><td><b>Safety</b></td><td><span class="yes">✓ Yes</span></td><td>Small chat models get lots of safety training, so they already recognise harmful requests and refusals. They just never learned to use that when <i>grading</i> someone else.</td><td><span class="yes">✓ Yes</span>, as Result 2 shows</td></tr>
<tr><td><b>Finance</b></td><td><span class="meh">~ Partly</span></td><td>Grading needs real finance maths. Most of what it "knows" is cheap clues like answer length.</td><td><span class="meh">~ Little to gain</span></td></tr>
<tr><td><b>Hard questions</b></td><td><span class="no">✗ No</span></td><td>Too hard for a model this small, and it mostly just picks the first answer.</td><td><span class="no">✗ No</span>, at most removing the first-answer habit</td></tr>
</table></div>
<p class="small muted" style="margin:10px 0 0">This matches the article's main claim: editing weights can <b>remove a blockage</b> but can't <b>add an ability</b> the model doesn't have.</p>
</div>

<!-- ===================================================== MEANING FOR JURIES -->
<div class="kicker">What it means for AI juries</div>
<h2>Check each judge topic by topic</h2>
<div class="grid g3" style="margin-top:12px">
  <div class="card takeaway"><h3>Verdicts can undersell a judge</h3><p class="small" style="color:var(--ink2);margin:4px 0 0">On safety, this judge's verdict is a coin flip, but its insides score <span class="num" id="m_k"></span>. A jury that picks judges by their verdicts alone would throw a capable judge away.</p></div>
  <div class="card takeaway"><h3>Skill depends on the topic</h3><p class="small" style="color:var(--ink2);margin:4px 0 0">The same small judge is capable on safety and useless on hard questions. A jury has to certify each judge per topic, not once overall.</p></div>
  <div class="card takeaway"><h3>Cheap judges could do more</h3><p class="small" style="color:var(--ink2);margin:4px 0 0">If a 0.8B judge can be repaired on a topic, it can handle more of the easy work in a cheap-then-expensive cascade. That's the one jury setup in this project that has beaten the single best judge.</p></div>
</div>

<!-- ===================================================== NEXT -->
<div class="kicker">Next</div>
<h2>What we'll try next</h2>
<div class="grid g3" style="margin-top:12px">
  <div class="card step"><div class="n">NEXT</div><h3>A safety-only edit</h3><div class="what">The same small edit, fitted so it stays silent on ordinary writing and on finance, and only fires on safety verdicts.</div></div>
  <div class="card step"><div class="n">THEN</div><h3>Compare with normal training</h3><div class="what">Fine-tune (LoRA) on the same examples, to check that hand-editing actually beats ordinary training.</div></div>
  <div class="card step"><div class="n">THEN</div><h3>Let Claude do the editing</h3><div class="what">Give Claude the weights and a small test budget, as the article did with its AI, and see whether it finds the fix on its own.</div></div>
</div>

<details><summary>Details for the team: methods, all numbers, caveats</summary>
<ul class="small" style="color:var(--ink2)">
<li><b>Judge:</b> Qwen3.5-0.8B, thinking off. The verdict is read from the next token after "VERDICT:". Benchmarks: RewardBench 2 Safety (900 items), BFF-Bench real answers (459), JudgeBench GPT-4o pairs in both orders (700).</li>
<li><b>Splits:</b> 60/20/20 train/dev/test, split by prompt/question/pair. Detector layer and all edit settings were chosen on dev; test was scored once.</li>
<li><b>"Knows":</b> a linear detector on one layer's internal state. The Result 1 chart uses 5-fold cross-validation, scored within groups that share a shortcut: same response model and refusal style (Safety), same answer model (BFF), same category (JudgeBench).</li>
<li><b>Result 2:</b> at layer 17, add strength × the detector's score × the model's own "says CORRECT" direction, at the verdict word only.</li>
<li><b>Result 3:</b> a rank-1 change to the output weights (down_proj columns) of 256 layer-16 neurons, chosen to track the detector on the training split. Saved as a diff in step2_edit_diff.safetensors.</li>
<li><b>Caveats:</b> the safety fix uses about 540 labeled examples, while the team's big judges (0.81–0.85 on the same data) are zero-shot, so this is not a fair head-to-head. Part of the safety "knowledge" may be word-level cues: even layer 1 scores 0.79.</li>
</ul>
<div class="wrap"><table class="det" id="tbl"></table></div>
</details>
</main>
<div class="tip" id="tip"></div>
<script>
const D=__DATA__, S1=__STEP1__, S2=__STEP2__, S2A=__STEP2A__;
const NAMES={rb2safety:"Safety",bff:"Finance (BFF)",judgebench:"Hard questions (JudgeBench)"};
const ORDER=["rb2safety","bff","judgebench"].filter(b=>D[b]);
const tip=document.getElementById("tip");
const f2=v=>(v==null||isNaN(v))?"–":v.toFixed(2),pct=v=>Math.round(v*100)+"%";
function showTip(e,h){tip.innerHTML=h;tip.style.display="block";const x=Math.min(e.pageX+12,scrollX+innerWidth-tip.offsetWidth-8);tip.style.left=x+"px";tip.style.top=(e.pageY+14)+"px";}
function hideTip(){tip.style.display="none";}
const NS="http://www.w3.org/2000/svg";
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e;}
function txt(p,x,y,s,cls,anchor){const t=el("text",{x,y,"text-anchor":anchor||"start"},p);if(cls)t.setAttribute("class",cls);t.textContent=s;return t;}
function hover(n,h){n.addEventListener("mousemove",e=>showTip(e,h));n.addEventListener("mouseleave",hideTip);}
const set=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v;};
const fair=b=>({says:D[b].cv_all.verdict_strat,knows:D[b].cv_all.probe_strat,short:D[b].cv_all.surface_strat});
const SF=fair("rb2safety");

// ---------- hero tiles
(function(){const H=document.getElementById("hero");const t=(lbl,big,sub)=>H.insertAdjacentHTML("beforeend",`<div class="card"><div class="lbl">${lbl}</div><div class="big">${big}</div><div class="sub">${sub}</div></div>`);
  t("Safety: says vs knows",`${f2(SF.says)}<span class="arrow">vs</span><span style="color:var(--knows)">${f2(SF.knows)}</span>`,"its verdict is a coin flip, but its insides know");
  if(S1)t("Connect it while it runs",`${f2(S1.baseline.auroc)}<span class="arrow">→</span><span style="color:var(--knows)">${f2(S1.knows.auroc)}</span>`,"safety score on held-out answers");
  if(S2)t("Build it into the weights",`${f2(S2.rb2safety_test.after.auroc)} <span style="font-size:18px;color:var(--bad)">but breaks</span>`,`finance ${f2(S2.bff.auroc_before)} → ${f2(S2.bff.auroc_after)}, and normal writing`);
})();

// ---------- concept diagram
(function(){const host=document.getElementById("diagram");const W=900,H=150;
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,role:"img","aria-label":"Answer goes in, middle layers know, verdict says; the link between them is missing"},host);
  const box=(x,w,title,sub,col)=>{el("rect",{x,y:34,width:w,height:76,rx:12,fill:"var(--chip)",stroke:col||"var(--ring)","stroke-width":col?2:1},svg);txt(svg,x+w/2,66,title,"lab","middle");txt(svg,x+w/2,88,sub,"lab2","middle");};
  box(10,190,"Answer to grade","e.g. a reply to a risky request");
  box(300,250,"Middle layers","work out “this looks fine”","var(--knows)");
  box(670,220,"Final word","says GOOD or BAD","var(--says)");
  const arr=(x1,x2,dash,col)=>{el("line",{x1,y1:72,x2:x2-8,y2:72,stroke:col||"var(--axis)","stroke-width":2.5,"stroke-dasharray":dash||""},svg);el("path",{d:`M${x2-10},65 L${x2},72 L${x2-10},79`,fill:"none",stroke:col||"var(--axis)","stroke-width":2.5},svg);};
  arr(202,298);arr(552,668,"6 6","var(--bad)");
  txt(svg,325,24,"KNOWS","val").style.fill="var(--knows)";txt(svg,695,24,"SAYS","val").style.fill="var(--says)";
  txt(svg,610,62,"missing","val","middle").style.fill="var(--bad)";txt(svg,610,100,"link","val","middle").style.fill="var(--bad)";
  txt(svg,W/2,H-6,"We measure both ends, then try to add the missing link.","ann","middle");
})();

// ---------- what we ran
(function(){const host=document.getElementById("steps");const c=(n,t,what,res)=>host.insertAdjacentHTML("beforeend",`<div class="card step"><div class="n">${n}</div><h3>${t}</h3><div class="what">${what}</div><div class="res">${res}</div></div>`);
  c("1 · THE CHECK","Look inside the judge","On 2,059 answers across three topics, we compared its verdict with a simple detector that reads its internal state.",`<b>Result:</b> on safety it knows (${f2(SF.knows)}) far more than it says (${f2(SF.says)}).`);
  if(S1)c("2 · CONNECT IT WHILE IT RUNS","Feed it its own knowledge","While it runs, push its final word in the direction its middle layers point. No weights changed.",`<b>Result:</b> safety ${f2(S1.baseline.auroc)} → <b>${f2(S1.knows.auroc)}</b>.`);
  if(S2)c("3 · BUILD IT IN","Edit the weights permanently",`Change the output weights of ${S2.chosen.n} neurons (${(S2.frac_weights*100).toFixed(2)}% of the model), with no outside help.`,`<b>Result:</b> safety ${f2(S2.rb2safety_test.before.auroc)} → <b>${f2(S2.rb2safety_test.after.auroc)}</b>, but finance and normal writing break.`);
})();

// ---------- result 1: dumbbell
(function(){const W=900,rowH=78,top=36,H=top+rowH*ORDER.length+30,L=240,R=W-40,x=v=>L+(v-0.5)/0.5*(R-L);
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,role:"img","aria-label":"Says vs knows by topic"},document.getElementById("dumbbell"));
  for(const t of [0.5,0.6,0.7,0.8,0.9,1.0]){el("line",{x1:x(t),x2:x(t),y1:top-12,y2:H-30,stroke:t===0.5?"var(--axis)":"var(--grid)","stroke-width":1},svg);txt(svg,x(t),H-10,t.toFixed(1),null,"middle");}
  txt(svg,x(0.5),top-18,"coin flip","ann","middle");txt(svg,x(1.0),top-18,"perfect","ann","middle");
  const tag={rb2safety:"Knows, doesn't say",bff:"Mostly cheap clues",judgebench:"Doesn't know"};
  ORDER.forEach((b,i)=>{const f=fair(b),y=top+22+i*rowH;
    txt(svg,0,y-2,NAMES[b],"lab");txt(svg,0,y+17,tag[b],"lab2");
    el("line",{x1:x(f.says),x2:x(f.knows),y1:y,y2:y,stroke:"var(--knows)","stroke-width":8,"stroke-linecap":"round",opacity:.22},svg);
    el("circle",{cx:x(f.short),cy:y,r:8,fill:"none",stroke:"var(--short)","stroke-width":2.5},svg);
    el("circle",{cx:x(f.says),cy:y,r:9,fill:"var(--says)",stroke:"var(--surface)","stroke-width":2},svg);
    el("circle",{cx:x(f.knows),cy:y,r:9,fill:"var(--knows)",stroke:"var(--surface)","stroke-width":2},svg);
    txt(svg,x(f.says),y+28,"says "+f2(f.says),"ann","middle");txt(svg,x(f.knows),y-16,"knows "+f2(f.knows),"val","middle");
    // "hidden" = knowledge beyond BOTH the verdict and the cheap clues
    const g=f.knows-Math.max(f.says,f.short);if(g>0.1){const t=txt(svg,(Math.max(x(f.says),x(f.short))+x(f.knows))/2,y-10,`hidden: +${g.toFixed(2)}`,"val","middle");t.style.fill="var(--knows)";}
    hover(el("rect",{x:0,y:y-32,width:W,height:64,fill:"transparent"},svg),`<b>${NAMES[b]}</b><br>Says: ${f2(f.says)}<br>Knows: ${f2(f.knows)}<br>Cheap clues alone: ${f2(f.short)}`);});
})();

// ---------- topic cards
(function(){const host=document.getElementById("topics");const J=D.judgebench,B=fair("bff"),Jf=fair("judgebench");
  const c=(t,chip,body)=>host.insertAdjacentHTML("beforeend",`<div class="card takeaway"><h3>${t}<span class="chip">${chip}</span></h3><p class="small" style="color:var(--ink2);margin:6px 0 0">${body}</p></div>`);
  c("Safety","Knows, doesn't say",`Calls almost everything bad (says "good" only ${pct(D.rb2safety.says_pos_test)} of the time), yet its insides tell good from bad at ${f2(SF.knows)}. <b>Worth fixing.</b>`);
  c("Finance","Mostly cheap clues",`Its insides score ${f2(B.knows)}, but cheap clues like answer length already get ${f2(B.short)}. <b>Little real knowledge hidden.</b>`);
  c("Hard questions","Doesn't know",`Near chance inside and out (${f2(Jf.says)} / ${f2(Jf.knows)}), and it picks the first answer ${pct(J.says_A_test)} of the time. <b>Nothing to connect.</b>`);
})();

// ---------- result 2 chart
(function(){if(!S1)return;set("r2_b",f2(S1.baseline.auroc));set("r2_a",f2(S1.knows.auroc));set("r2_sa",pct(S1.knows.says_correct));set("r2_sb",pct(S1.baseline.says_correct));set("r2_c",f2(S1.constant.auroc));
  const host=document.getElementById("r2chart");host.insertAdjacentHTML("afterbegin",`<h3>Safety score on held-out answers</h3><p class="small muted" style="margin:0 0 6px">0.5 = coin flip · whiskers = 95% range</p>`);
  const rows=[["Original judge",S1.baseline,"var(--says)",1],["Push all toward “good”",S1.constant,"var(--short)",1],["Connect its knowledge",S1.knows,"var(--knows)",1]];
  const W=440,H=36+rows.length*54,L=170,R=W-50,x=v=>L+(v-0.4)/0.6*(R-L);
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,role:"img","aria-label":"Result 2 chart"},host);
  for(const t of [0.5,0.75,1.0]){el("line",{x1:x(t),x2:x(t),y1:4,y2:H-24,stroke:t===0.5?"var(--axis)":"var(--grid)"},svg);txt(svg,x(t),H-6,t===0.5?"0.5":t.toFixed(2),null,"middle");}
  rows.forEach(([nm,r,c],i)=>{const y=14+i*54;txt(svg,L-10,y+19,nm,"lab","end");
    const b=el("rect",{x:x(0.4),y,width:Math.max(2,x(r.auroc)-x(0.4)),height:28,rx:5,fill:c},svg);
    if(r.auroc_ci)el("line",{x1:x(r.auroc_ci[0]),x2:x(r.auroc_ci[1]),y1:y+14,y2:y+14,stroke:"var(--ink)","stroke-width":1.5,opacity:.5},svg);
    txt(svg,x(r.auroc)+6,y+19,f2(r.auroc),"val");hover(b,`<b>${nm}</b><br>Score ${f2(r.auroc)}<br>Says good: ${pct(r.says_correct)}`);});
})();

// ---------- result 3 chart + generation example
(function(){if(!S2)return;const rb=S2.rb2safety_test;
  set("r3_n",S2.chosen.n);set("r3_frac",(S2.frac_weights*100).toFixed(2)+"%");set("r3_rb_b",f2(rb.before.auroc));set("r3_rb_a",f2(rb.after.auroc));
  set("r3_bff_b",f2(S2.bff.auroc_before));set("r3_bff_a",f2(S2.bff.auroc_after));if(S2A)set("r3_abl",f2(Math.max(...S2A.map(r=>r.auroc))));
  const host=document.getElementById("r3chart");host.insertAdjacentHTML("afterbegin",`<h3>Before vs. after the permanent edit</h3><p class="small muted" style="margin:0 0 6px">Judge score on held-out answers (0.5 = coin flip)</p>`);
  const rows=[["Safety",rb.before.auroc,rb.after.auroc,"✓ fixed"],["Finance",S2.bff.auroc_before,S2.bff.auroc_after,"✗ broken"],["Hard questions",S2.judgebench.auroc_before,S2.judgebench.auroc_after,"– no change"]];
  const W=440,H=40+rows.length*64,L=110,R=W-70,x=v=>L+(v-0.4)/0.6*(R-L);
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,role:"img","aria-label":"Result 3 chart"},host);
  for(const t of [0.5,0.75,1.0]){el("line",{x1:x(t),x2:x(t),y1:4,y2:H-24,stroke:t===0.5?"var(--axis)":"var(--grid)"},svg);txt(svg,x(t),H-6,t===0.5?"0.5":t.toFixed(2),null,"middle");}
  rows.forEach(([nm,b,a,verdict],i)=>{const y=12+i*64;txt(svg,L-10,y+20,nm,"lab","end");
    const better=a>b+0.02,worse=a<b-0.02,c=better?"var(--knows)":worse?"var(--says)":"var(--short)";
    const r1=el("rect",{x:x(0.4),y,width:Math.max(2,x(b)-x(0.4)),height:18,rx:4,fill:"var(--short)",opacity:.45},svg);txt(svg,x(b)+6,y+13,"before "+f2(b),"ann");
    const r2=el("rect",{x:x(0.4),y:y+22,width:Math.max(2,x(a)-x(0.4)),height:18,rx:4,fill:c},svg);txt(svg,x(a)+6,y+35,"after "+f2(a),"val");
    const v=txt(svg,L-10,y+42,verdict,"val","end");v.style.fill=better?"var(--good)":worse?"var(--bad)":"var(--muted)";
    hover(r1,`${nm} before: ${f2(b)}`);hover(r2,`${nm} after: ${f2(a)}`);});
  const g0=S2.generations_before[0],g1=S2.generations_after[0],esc=s=>s.replace(/[<&]/g,c=>c==="<"?"&lt;":"&amp;");
  document.getElementById("gen").innerHTML=`<div class="card"><h3>Before the edit <span class="chip">normal</span></h3><p class="small muted" style="margin:2px 0 8px">"${esc(g0.prompt)}"</p><div class="gen">${esc(g0.text.slice(0,210))}…</div></div>
    <div class="card"><h3>After the edit <span class="chip">broken</span></h3><p class="small muted" style="margin:2px 0 8px">same prompt</p><div class="gen">${esc(g1.text.slice(0,150))}…</div></div>`;
})();
set("m_k",f2(SF.knows));

// ---------- details table
document.getElementById("tbl").innerHTML="<tr><th>Topic</th><th>Items (test)</th><th>Same-source: says / knows / clues</th><th>Test split: says / knows (layer) / clues</th></tr>"+
ORDER.map(b=>{const s=D[b],f=fair(b);return `<tr><td>${NAMES[b]}</td><td>${s.n} (${s.n_test})</td><td>${f2(f.says)} / ${f2(f.knows)} / ${f2(f.short)}</td><td>${f2(s.verdict_auroc)} / ${f2(s.probe_auroc)} (L${s.probe_layer}) / ${f2(s.surface_auroc)}</td></tr>`}).join("");
</script></body></html>"""


def main():
    opt = lambda name: json.loads((RES / name).read_text()) if (RES / name).exists() else None
    html = TEMPLATE
    for key, val in (("__DATA__", opt("gap_summary.json")), ("__STEP1__", opt("step1_test.json")),
                     ("__STEP2__", opt("step2_final.json")), ("__STEP2A__", opt("step2_ablate_dev.json"))):
        html = html.replace(key, json.dumps(val))
    (RES / "gap_report.html").write_text(html)
    print("wrote", RES / "gap_report.html")


if __name__ == "__main__":
    main()
