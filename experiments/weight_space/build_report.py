#!/usr/bin/env python3
"""Build results/gap_report.html (self-contained, inline SVG, light + dark) from results/gap_summary.json.

The page tells one story: does the small judge KNOW more than it SAYS? Headline numbers are the "fair" ones:
5-fold CV over all items, scored only within groups that share the obvious shortcut (same answer model /
same response model + refusal style / same category), so a probe can't win by spotting who wrote the answer.

  .venv/bin/python experiments/weight_space/build_report.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Judge Gap Check</title>
<style>
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;
--axis:#c3c2b7;--ring:rgba(11,11,11,.10);--says:#eb6834;--knows:#2a78d6;--short:#898781;--good:#1baf7a;--bad:#eb6834;--chip:#f0efec}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;
--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);
--says:#d95926;--knows:#3987e5;--short:#898781;--good:#199e70;--bad:#d95926;--chip:#262624}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;
--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--says:#d95926;--knows:#3987e5;--short:#898781;--good:#199e70;
--bad:#d95926;--chip:#262624}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
main{max-width:960px;margin:0 auto;padding:36px 16px 72px}
h1{font-size:30px;line-height:1.2;margin:0 0 8px}h2{font-size:21px;margin:44px 0 6px}h3{font-size:17px;margin:0}
p{margin:6px 0}.lead{font-size:17px;color:var(--ink2);max-width:760px}.muted{color:var(--muted)}.small{font-size:13.5px}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:12px;padding:18px 18px 14px;position:relative}
.how{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:18px 0 0}
.how .card{padding:14px 16px}.how b{display:block;font-size:15px;margin-bottom:2px}.how .card p{font-size:14px;color:var(--ink2);margin:0}
.key{display:inline-flex;align-items:center;gap:6px;margin-right:16px;font-size:14px;color:var(--ink2)}
.dot{width:12px;height:12px;border-radius:50%;display:inline-block}.ring{width:12px;height:12px;border-radius:50%;border:2px solid var(--short);display:inline-block}
.verdict{display:inline-block;font-size:13px;font-weight:600;padding:2px 10px;border-radius:999px;background:var(--chip);color:var(--ink);margin-left:8px;vertical-align:2px}
.story{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:22px;align-items:center;margin-top:12px}
@media (max-width:760px){.story{grid-template-columns:1fr}}
.story ul{margin:8px 0 0;padding-left:20px}.story li{margin:4px 0}
.big{font-size:15px}.num{font-variant-numeric:tabular-nums;font-weight:600}
svg{display:block;width:100%;height:auto;overflow:visible}
svg text{fill:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}svg .lab{fill:var(--ink);font-size:13.5px;font-weight:500}
svg .lab2{fill:var(--ink2);font-size:12px}svg .ann{fill:var(--ink2);font-size:12px}svg .val{fill:var(--ink);font-size:12px;font-weight:600}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-top:14px}
.steps .card{padding:14px 16px}.steps .n{font-size:12px;color:var(--muted);font-weight:600;letter-spacing:.04em}
.steps b{display:block;margin:2px 0}.steps p{font-size:14px;color:var(--ink2);margin:0}
.tip{position:absolute;pointer-events:none;background:var(--surface);color:var(--ink);border:1px solid var(--ring);border-radius:8px;
padding:6px 9px;font-size:12.5px;box-shadow:0 4px 14px rgba(0,0,0,.14);display:none;white-space:nowrap;z-index:5}
details{margin-top:40px}summary{cursor:pointer;color:var(--ink2);font-size:15px}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums;margin-top:10px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid);vertical-align:top}th{color:var(--ink2);font-weight:500}
.wrap{overflow-x:auto}
</style></head><body><main>

<h1>Does the AI judge know more than it says?</h1>
<p class="lead">We used a small model, Qwen3.5-0.8B, as a judge: it reads an answer and says <b>good</b> or <b>bad</b>. Then we looked inside it to see whether it had worked out the right call but didn't say it.</p>
<p class="lead">This matters for the next step. Editing a model's weights can remove a blockage, but it can't add knowledge the model doesn't have. So first we had to check whether the knowledge is there at all.</p>

<div class="how">
  <div class="card"><b>1. What it says</b><p>The judge's own verdict: how strongly it leans "good" vs "bad".</p></div>
  <div class="card"><b>2. What it knows</b><p>A simple detector reads the judge's internal numbers while it decides, and predicts good/bad from those alone.</p></div>
  <div class="card"><b>3. Shortcut check</b><p>How well do cheap clues alone do, like "this source usually writes bad answers"? Scores are compared only among answers from the same source, so the detector can't win by spotting who wrote the answer.</p></div>
  <div class="card"><b>Score scale</b><p>0.5 = coin flip<br>1.0 = perfect at telling good from bad<br><span class="muted">(AUROC)</span></p></div>
</div>

<h2>The answer, in one picture</h2>
<p>The gap between <span style="color:var(--says);font-weight:600">says</span> and <span style="color:var(--knows);font-weight:600">knows</span> is knowledge the judge has but doesn't use.</p>
<div class="card" id="main" style="margin-top:12px"></div>
<p class="small muted" style="margin-top:8px"><span class="key"><span class="dot" style="background:var(--says)"></span>What it says (verdict)</span><span class="key"><span class="dot" style="background:var(--knows)"></span>What it knows (hidden-state detector)</span><span class="key"><span class="ring"></span>Shortcut clues alone</span></p>

<h2>RewardBench Safety <span class="verdict">Knows, but doesn't say</span></h2>
<div class="story">
  <div class="big">
    <p>The task is to judge whether a response to a risky request is appropriate.</p>
    <ul>
      <li>It <b>calls almost everything bad</b>: it says "good" on only <span class="num" id="rb_saysgood"></span> of answers. Its verdict is a coin flip (<span class="num" id="rb_says"></span>).</li>
      <li>Inside, it <b>knows</b> which answers are fine (<span class="num" id="rb_knows"></span>), even when we compare only responses from the same source.</li>
      <li>The knowledge appears by about the middle of the network and stays there. It just never reaches the final word.</li>
    </ul>
    <p style="margin-top:10px"><b>Best place to try a weight edit.</b></p>
  </div>
  <div class="card" id="rb_layers"></div>
</div>

<h2>BFF-Bench (finance) <span class="verdict">Partly knows, shortcuts mixed in</span></h2>
<div class="story">
  <div class="big">
    <p>The task is to judge whether a finance or accounting answer is correct.</p>
    <ul>
      <li>It says somewhat better than chance (<span class="num" id="bff_says"></span>).</li>
      <li>Inside, it knows more (<span class="num" id="bff_knows"></span>)...</li>
      <li>...but cheap clues like answer length already get <span class="num" id="bff_short"></span>, so only part of that is real judgment.</li>
    </ul>
    <p style="margin-top:10px"><b>A cleaner test needs answers that differ by just one planted mistake.</b></p>
  </div>
  <div class="card" id="bff_bars"></div>
</div>

<h2>JudgeBench (which answer is better?) <span class="verdict">Doesn't know, and favours "A"</span></h2>
<div class="story">
  <div class="big">
    <p>The task is to pick the better of two answers to hard questions.</p>
    <ul>
      <li>It says and knows about the same, close to a coin flip (<span class="num" id="jb_says"></span> vs <span class="num" id="jb_knows"></span>). The questions are too hard for a model this small.</li>
      <li>It picks <b>whichever answer is shown first</b> <span class="num" id="jb_a"></span> of the time. The correct answer is first only 50% of the time.</li>
      <li>Correcting for that habit lifts it to <span class="num" id="jb_deb"></span>.</li>
    </ul>
    <p style="margin-top:10px"><b>Editing can't add the missing knowledge, but it might remove the "A" habit.</b></p>
  </div>
  <div class="card" id="jb_bias"></div>
</div>

<h2>What's next</h2>
<p>Try to make the safety judge <i>say</i> what it already <i>knows</i>, in four increasingly hands-off ways, and compare them:</p>
<div class="steps">
  <div class="card"><div class="n">STEP 1</div><b>Nudge while it runs</b><p>Push its internal state in the "this is fine" direction. Weights untouched.</p></div>
  <div class="card"><div class="n">STEP 2</div><b>Hand-made weight edit</b><p>A small, targeted change to a few weights, like the article's Experiment 8.</p></div>
  <div class="card"><div class="n">STEP 3</div><b>Normal training</b><p>Ordinary fine-tuning (LoRA) on the same examples, as the comparison.</p></div>
  <div class="card"><div class="n">STEP 4</div><b>Claude edits the weights</b><p>Claude gets the weights and a small test budget, like the article's AI editor.</p></div>
</div>

<details><summary>Details: methods, all numbers, caveats</summary>
<ul class="small" style="color:var(--ink2)">
<li>Judge: Qwen3.5-0.8B, thinking off, verdict read from the next token after "VERDICT:". All items: __NITEMS__.</li>
<li>Headline numbers (chart above): 5-fold cross-validation grouped by question/pair/prompt, scored within groups that share the shortcut: same answer model (BFF), same response model and refusal style (Safety), same category (JudgeBench).</li>
<li>The held-out test split (columns below, probe layer chosen on a separate dev split) agrees; BFF's test split has only ~15 questions, so its intervals are wide.</li>
<li>Safety: without the same-source restriction, shortcuts alone reach 0.97, because some sources (e.g. a 0.5B model, jailbreak responses) are always the bad ones. That is why the headline compares within source.</li>
<li>Layer chart: dev split. "Would say at this layer" = that layer read through the model's own output head (logit lens).</li>
</ul>
<div class="wrap"><table id="tbl"></table></div>
</details>
</main>
<div class="tip" id="tip"></div>
<script>
const D = __DATA__;
const NAMES={rb2safety:"RewardBench Safety",bff:"BFF-Bench (finance)",judgebench:"JudgeBench (pairs)"};
const ORDER=["rb2safety","bff","judgebench"].filter(b=>D[b]);
const tip=document.getElementById("tip");
const f2=v=>(v==null||isNaN(v))?"–":v.toFixed(2), pct=v=>Math.round(v*100)+"%";
function showTip(e,h){tip.innerHTML=h;tip.style.display="block";const x=Math.min(e.pageX+12,scrollX+innerWidth-tip.offsetWidth-8);tip.style.left=x+"px";tip.style.top=(e.pageY+14)+"px";}
function hideTip(){tip.style.display="none";}
const NS="http://www.w3.org/2000/svg";
function el(t,a,p){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e;}
function txt(p,x,y,s,cls,anchor){const t=el("text",{x,y,"text-anchor":anchor||"start"},p);if(cls)t.setAttribute("class",cls);t.textContent=s;return t;}
function hover(node,html){node.addEventListener("mousemove",e=>showTip(e,html));node.addEventListener("mouseleave",hideTip);}
const fair=b=>({says:D[b].cv_all.verdict_strat,knows:D[b].cv_all.probe_strat,short:D[b].cv_all.surface_strat});

// fill numbers in the text
const S=fair("rb2safety"),B=fair("bff"),J=fair("judgebench");
const set=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v;};
set("rb_saysgood",pct(D.rb2safety.says_pos_test));set("rb_says",f2(S.says));set("rb_knows",f2(S.knows));
set("bff_says",f2(B.says));set("bff_knows",f2(B.knows));set("bff_short",f2(B.short));
set("jb_says",f2(J.says));set("jb_knows",f2(J.knows));set("jb_a",pct(D.judgebench.says_A_test));set("jb_deb",f2(D.judgebench.debiased_pair_auroc));

// 1. main dumbbell: says -> knows per benchmark, shortcut ring
(function(){const W=880,rowH=74,top=34,H=top+rowH*ORDER.length+30,L=210,R=W-40,x=v=>L+(v-0.5)/0.5*(R-L);
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,role:"img","aria-label":"What the judge says vs knows, per benchmark"},document.getElementById("main"));
  for(const t of [0.5,0.6,0.7,0.8,0.9,1.0]){el("line",{x1:x(t),x2:x(t),y1:top-12,y2:H-30,stroke:t===0.5?"var(--axis)":"var(--grid)","stroke-width":1},svg);txt(svg,x(t),H-10,t.toFixed(1),null,"middle");}
  txt(svg,x(0.5),top-18,"coin flip","ann","middle");txt(svg,x(1.0),top-18,"perfect","ann","middle");
  const tag={rb2safety:"Knows, doesn't say",bff:"Partly knows",judgebench:"Doesn't know"};
  ORDER.forEach((b,i)=>{const f=fair(b),y=top+20+i*rowH;
    txt(svg,0,y-2,NAMES[b],"lab");txt(svg,0,y+16,tag[b],"lab2");
    el("line",{x1:x(f.says),x2:x(f.knows),y1:y,y2:y,stroke:"var(--knows)","stroke-width":6,"stroke-linecap":"round",opacity:.22},svg);
    el("circle",{cx:x(f.short),cy:y,r:8,fill:"none",stroke:"var(--short)","stroke-width":2.5},svg);
    el("circle",{cx:x(f.says),cy:y,r:8,fill:"var(--says)",stroke:"var(--surface)","stroke-width":2},svg);
    el("circle",{cx:x(f.knows),cy:y,r:8,fill:"var(--knows)",stroke:"var(--surface)","stroke-width":2},svg);
    const gap=f.knows-f.says;
    txt(svg,x(f.says),y+27,"says "+f2(f.says),"ann","middle");
    txt(svg,x(f.knows),y-15,"knows "+f2(f.knows),"val","middle");
    if(gap>0.1)txt(svg,(x(f.says)+x(f.knows))/2,y+5,"+"+gap.toFixed(2),"val","middle").setAttribute("dy","-14");
    const hit=el("rect",{x:0,y:y-30,width:W,height:60,fill:"transparent"},svg);
    hover(hit,`<b>${NAMES[b]}</b><br>Says: ${f2(f.says)}<br>Knows: ${f2(f.knows)}<br>Shortcut clues alone: ${f2(f.short)}<br><span style="color:var(--muted)">within ${D[b].strat_name.replace(/ \(.*\)/,"")}</span>`);});
})();

// 2. Safety: layer chart (knows vs would-say by layer)
(function(){const s=D.rb2safety,P=s.probe_dev_auroc_by_layer,Lz=s.lens_dev_auroc_by_layer,n=P.length;
  const host=document.getElementById("rb_layers");host.insertAdjacentHTML("afterbegin",`<h3>Knows early, never says it</h3><p class="small muted">Score at each of the model's 24 layers, input → output (all responses, so "knows" here includes shortcut clues)</p>`);
  const W=440,H=250,l=34,r=W-14,t=18,bt=H-34,x=i=>l+i/(n-1)*(r-l),y=v=>bt-(v-0.3)/0.7*(bt-t);
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,role:"img","aria-label":"Safety: knows vs would-say by layer"},host);
  for(const v of [0.3,0.5,0.7,0.9]){el("line",{x1:l,x2:r,y1:y(v),y2:y(v),stroke:v===0.5?"var(--axis)":"var(--grid)","stroke-width":1},svg);txt(svg,l-6,y(v)+4,v.toFixed(1),null,"end");}
  txt(svg,l,H-8,"input","ann");txt(svg,r,H-8,"output (verdict)","ann","end");txt(svg,(l+r)/2,H-8,"layer →",null,"middle");
  const path=(a,c)=>el("path",{d:a.map((v,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(Math.max(.3,v)).toFixed(1)}`).join(""),fill:"none",stroke:c,"stroke-width":2.5,"stroke-linejoin":"round","stroke-linecap":"round"},svg);
  path(Lz,"var(--says)");path(P,"var(--knows)");
  txt(svg,x(16),y(P[16])-10,"what it knows","val","middle").style.fill="var(--knows)";
  txt(svg,x(9),y(0.72),"what it would say","val","middle").style.fill="var(--says)";
  el("circle",{cx:x(n-1),cy:y(Lz[n-1]),r:5,fill:"var(--says)",stroke:"var(--surface)","stroke-width":2},svg);
  txt(svg,x(n-1)-6,y(Lz[n-1])+20,"final verdict "+f2(Lz[n-1]),"ann","end");
  const cross=el("line",{x1:0,x2:0,y1:t,y2:bt,stroke:"var(--axis)",visibility:"hidden"},svg);
  const hit=el("rect",{x:l,y:t,width:r-l,height:bt-t,fill:"transparent"},svg);
  hit.addEventListener("mousemove",e=>{const pt=svg.createSVGPoint();pt.x=e.clientX;pt.y=e.clientY;const p=pt.matrixTransform(svg.getScreenCTM().inverse());
    const i=Math.max(0,Math.min(n-1,Math.round((p.x-l)/(r-l)*(n-1))));cross.setAttribute("x1",x(i));cross.setAttribute("x2",x(i));cross.setAttribute("visibility","visible");
    showTip(e,`<b>Layer ${i}</b><br>Knows: ${f2(P[i])}<br>Would say: ${f2(Lz[i])}`);});
  hit.addEventListener("mouseleave",()=>{cross.setAttribute("visibility","hidden");hideTip();});
})();

// 3. BFF: three bars, says / shortcuts / knows
(function(){const host=document.getElementById("bff_bars");host.insertAdjacentHTML("afterbegin",`<h3>Knows more, but shortcuts get close</h3><p class="small muted">Score within answers from the same source model</p>`);
  const rows=[["What it says",B.says,"var(--says)"],["Shortcut clues alone",B.short,"var(--short)"],["What it knows",B.knows,"var(--knows)"]];
  const W=440,H=40+rows.length*46,L=150,R=W-46,x=v=>L+(v-0.5)/0.5*(R-L);
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,role:"img","aria-label":"BFF says vs shortcuts vs knows"},host);
  for(const t of [0.5,0.75,1.0]){el("line",{x1:x(t),x2:x(t),y1:6,y2:H-24,stroke:t===0.5?"var(--axis)":"var(--grid)"},svg);txt(svg,x(t),H-6,t===0.5?"0.5 coin flip":t.toFixed(2),null,"middle");}
  rows.forEach(([nm,v,c],i)=>{const y=14+i*46;txt(svg,L-10,y+19,nm,"lab","end");
    const bar=el("rect",{x:x(0.5),y,width:x(v)-x(0.5),height:26,rx:4,fill:c},svg);txt(svg,x(v)+6,y+18,f2(v),"val");hover(bar,`${nm}: ${f2(v)}`);});
})();

// 4. JudgeBench: picks-A bar vs truth, then score steps
(function(){const s=D.judgebench,host=document.getElementById("jb_bias");host.insertAdjacentHTML("afterbegin",`<h3>It mostly just picks the first answer</h3><p class="small muted">Share of verdicts that pick answer A (the one shown first)</p>`);
  const W=440,H=262,L=130,R=W-46,x=v=>L+v*(R-L);
  const svg=el("svg",{viewBox:`0 0 ${W} ${H}`,role:"img","aria-label":"JudgeBench position bias"},host);
  const bar=(y,lbl,a,note)=>{txt(svg,L-10,y+19,lbl,"lab","end");
    const r1=el("rect",{x:x(0),y,width:x(a)-x(0)-1,height:28,rx:4,fill:"var(--says)"},svg);const r2=el("rect",{x:x(a)+1,y,width:x(1)-x(a)-1,height:28,rx:4,fill:"var(--short)",opacity:.45},svg);
    txt(svg,x(a)-8,y+19,"A "+pct(a),"val","end").style.fill="#fff";if(1-a<0.25)txt(svg,x(1)+6,y+19,"B "+pct(1-a),"val");else txt(svg,x(1)-8,y+19,"B "+pct(1-a),"val","end");
    hover(r1,`${lbl}: picks A ${pct(a)}`);hover(r2,`${lbl}: picks B ${pct(1-a)}`);};
  bar(10,"Judge",s.says_A_test);bar(50,"Correct pick",0.5);
  txt(svg,0,110,"Score (0.5 = coin flip)","lab");
  const steps=[["What it says",J.says,"var(--says)",1],["“A” habit removed",s.debiased_pair_auroc,"var(--says)",.55],["What it knows",J.knows,"var(--knows)",1]];
  const sx=v=>L+(v-0.5)/0.5*(R-L);
  for(const t of [0.5,0.75,1.0]){el("line",{x1:sx(t),x2:sx(t),y1:120,y2:H-22,stroke:t===0.5?"var(--axis)":"var(--grid)"},svg);txt(svg,sx(t),H-6,t.toFixed(2),null,"middle");}
  steps.forEach(([nm,v,c,op],i)=>{const y=124+i*38;txt(svg,L-10,y+17,nm,"lab","end");
    const b=el("rect",{x:sx(0.5),y,width:sx(v)-sx(0.5),height:24,rx:4,fill:c,opacity:op},svg);txt(svg,sx(v)+6,y+17,f2(v),"val");hover(b,`${nm}: ${f2(v)}`);});
})();

// table
document.getElementById("tbl").innerHTML="<tr><th>Benchmark</th><th>Items (test)</th><th>Same-source: says / knows / shortcuts</th><th>Test split: says / knows (layer) / shortcuts</th><th>Logit lens best</th></tr>"+
ORDER.map(b=>{const s=D[b],f=fair(b);return `<tr><td>${NAMES[b]}</td><td>${s.n} (${s.n_test})</td><td>${f2(f.says)} / ${f2(f.knows)} / ${f2(f.short)}</td><td>${f2(s.verdict_auroc)} [${f2(s.verdict_ci[0])}–${f2(s.verdict_ci[1])}] / ${f2(s.probe_auroc)} [${f2(s.probe_ci[0])}–${f2(s.probe_ci[1])}] (L${s.probe_layer}) / ${f2(s.surface_auroc)}</td><td>${f2(s.lens_auroc)} (L${s.lens_layer})</td></tr>`}).join("");
</script></body></html>"""


def main():
    data = json.loads((RES / "gap_summary.json").read_text())
    n = sum(s["n"] for s in data.values())
    html = TEMPLATE.replace("__DATA__", json.dumps(data)).replace("__NITEMS__", f"{n:,}")
    (RES / "gap_report.html").write_text(html)
    print("wrote", RES / "gap_report.html")


if __name__ == "__main__":
    main()
