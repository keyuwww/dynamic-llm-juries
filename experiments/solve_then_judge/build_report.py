#!/usr/bin/env python3
"""
HTML report for the solve-then-judge experiment, in the style of the team's "Judge Routing Update" page.
Reads results/metrics.json (analyze.py) and writes results/report.html. The peer chart appears once the peer
arm is in metrics.json; until then it shows as pending.

  uv run python experiments/solve_then_judge/build_report.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = {"gpt-oss-120b": "gpt-oss-120b", "gpt-oss-20b": "gpt-oss-20b", "deepseek-v3.1": "DeepSeek-V3.1",
        "qwen3.6-35b-a3b": "Qwen3.6-35B", "qwen3.5-9b": "Qwen3.5-9B", "qwen3.5-4b": "Qwen3.5-4B",
        "nemotron3-super-120b": "Nemotron-Super-120B", "nemotron3-nano-30b": "Nemotron-Nano-30B"}

CSS = """
/* Layout: findings first, then full-width charts, each with a one-line takeaway; same system as the Judge Routing Update */
:root{
  --bg:#f5f6f4; --surface:#ffffff; --ink:#18212b; --ink-2:#4b5662; --ink-3:#6c7682; --line:#dde1e3; --grid:#e6e9ea;
  --accent:#16645c; --accent-soft:#e3efec;
  --c1:#2a78d6; --c2:#eb6834; --c3:#1baf7a; --c4:#9aa3ac;
  --display:"Bricolage Grotesque","Avenir Next","Segoe UI",sans-serif;
  --body:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#12171c; --surface:#1a2027; --ink:#e7ebee; --ink-2:#b4bdc5; --ink-3:#8f9aa4; --line:#2c343c; --grid:#262d34;
  --accent:#5cc2b3; --accent-soft:#183330; --c1:#3987e5; --c2:#d95926; --c3:#199e70; --c4:#5b646d; color-scheme:dark } }
:root[data-theme="dark"]{
  --bg:#12171c; --surface:#1a2027; --ink:#e7ebee; --ink-2:#b4bdc5; --ink-3:#8f9aa4; --line:#2c343c; --grid:#262d34;
  --accent:#5cc2b3; --accent-soft:#183330; --c1:#3987e5; --c2:#d95926; --c3:#199e70; --c4:#5b646d; color-scheme:dark }
body{background:var(--bg);color:var(--ink);font:15px/1.6 var(--body)}
.wrap{max-width:980px;margin:0 auto;padding-block:40px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:44px}
.wrap>*,section.fig>*{min-width:0}
.eyebrow{font:500 12px/1.4 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
h1{font:700 clamp(30px,5vw,46px)/1.06 var(--display);margin:8px 0 0;text-wrap:balance;letter-spacing:-.01em;max-width:24ch}
h2{font:700 clamp(20px,2.6vw,25px)/1.22 var(--display);margin:0;text-wrap:balance}
p{margin:0;max-width:70ch}
.meta{font:13px/1.5 var(--mono);color:var(--ink-3);margin-top:12px}
ol.concl{margin:0;padding:0;list-style:none;display:grid;gap:12px;counter-reset:c}
ol.concl li{display:grid;grid-template-columns:34px minmax(0,1fr);gap:12px;align-items:start;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 16px;counter-increment:c}
ol.concl li::before{content:counter(c);font:700 22px/1 var(--display);color:var(--accent);padding-top:2px}
ol.concl b{display:block;font:600 16px/1.35 var(--body)}
ol.concl span{color:var(--ink-2);font-size:14px}
section.fig{display:grid;gap:10px}
.take{color:var(--ink-2);font-size:14.5px}
.chart{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 10px 8px;overflow-x:auto}
.chart svg{display:block;width:100%;min-width:620px;height:auto}
.chart text{font-family:var(--mono);font-size:11.5px;fill:var(--ink-3)}
.chart .lab{font-family:var(--body);font-size:13px;fill:var(--ink)}
.chart .val{font-size:11px;fill:var(--ink-2)}
.chart .gl{stroke:var(--grid);stroke-width:1}
.legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:13px;color:var(--ink-2)}
.legend span{display:inline-flex;align-items:center;gap:7px}
.legend i{display:inline-block;width:11px;height:11px;border-radius:50%}
.legend i.sq{border-radius:2px}
.legend i.ring{background:transparent!important;border:2px solid var(--ink-3);width:9px;height:9px}
.pending{background:var(--surface);border:1px dashed var(--line);border-radius:10px;padding:22px;color:var(--ink-3);font-size:14px}
.next{border-left:3px solid var(--accent);background:var(--accent-soft);padding:14px 18px;display:grid;gap:6px}
.next ul{margin:0;padding-left:18px;display:grid;gap:4px}
.note{font-size:12.5px;color:var(--ink-3);max-width:90ch}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);font:12px/1.4 var(--body);padding:6px 9px;border-radius:6px;opacity:0;transition:opacity .1s;z-index:5}
"""

JS = r"""
(function(){
  var D=JSON.parse(document.getElementById("data").textContent);
  var ns="http://www.w3.org/2000/svg", tip=document.getElementById("tip");
  function mk(svg){return function(t,a,txt){var e=document.createElementNS(ns,t);for(var k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;svg.appendChild(e);return e}}
  function hov(e,msg){e.setAttribute("tabindex","0");e.setAttribute("aria-label",msg);
    function s(){tip.textContent=msg;var r=e.getBoundingClientRect();tip.style.left=Math.min(r.left+r.width/2+10,innerWidth-280)+"px";tip.style.top=(r.top-34)+"px";tip.style.opacity=1}
    function h(){tip.style.opacity=0}
    e.addEventListener("mouseenter",s);e.addEventListener("focus",s);e.addEventListener("mouseleave",h);e.addEventListener("blur",h)}

  // 1. accuracy per arm, dot plot
  var A=D.arms, s1=document.getElementById("g1"), e1=mk(s1), L1=200, rh=40, lo=60, hi=95, W=900, R=60;
  var X1=function(v){return L1+(W-L1-R)*(v-lo)/(hi-lo)};
  var H1=20+rh*A.length+50; s1.setAttribute("viewBox","0 0 900 "+H1);
  for(var t=lo;t<=hi;t+=5){e1("line",{class:"gl",x1:X1(t),x2:X1(t),y1:10,y2:14+rh*A.length});e1("text",{x:X1(t),y:32+rh*A.length,"text-anchor":"middle"},t+"%")}
  e1("text",{x:(L1+W-R)/2,y:52+rh*A.length,"text-anchor":"middle"},"agreement with the human label (808 BFF responses)");
  var arms=[["none","var(--c4)","no reference"],["self","var(--c2)","its own answer"],["peer","var(--c1)","gpt-oss-120b's answer"],["human","var(--c3)","expert reference"]];
  A.forEach(function(r,i){var y=14+rh*i+rh/2;
    e1("text",{class:"lab",x:L1-14,y:y+4,"text-anchor":"end"},r.name);
    var vs=arms.filter(function(a){return r[a[0]]!=null}).map(function(a){return r[a[0]]});
    e1("line",{x1:X1(Math.min.apply(null,vs)),x2:X1(Math.max.apply(null,vs)),y1:y,y2:y,stroke:"var(--line)","stroke-width":2});
    arms.forEach(function(a){if(r[a[0]]==null)return;
      var c=e1("circle",{cx:X1(r[a[0]]),cy:y,r:7,fill:a[0]==="none"?"var(--surface)":a[1],stroke:a[0]==="none"?"var(--ink-3)":"var(--surface)","stroke-width":2});
      hov(c,r.name+", "+a[2]+": "+r[a[0]].toFixed(1)+"%")});
  });

  // 2. self minus none, when the judge solved vs failed the question
  var S=D.split, s2=document.getElementById("g2"), e2=mk(s2), L2=200, rh2=46, lo2=-20, hi2=10, R2=60;
  var X2=function(v){return L2+(W-L2-R2)*(v-lo2)/(hi2-lo2)};
  var H2=20+rh2*S.length+50; s2.setAttribute("viewBox","0 0 900 "+H2);
  for(var t2=lo2;t2<=hi2;t2+=5){e2("line",{class:"gl",x1:X2(t2),x2:X2(t2),y1:10,y2:14+rh2*S.length});e2("text",{x:X2(t2),y:32+rh2*S.length,"text-anchor":"middle"},(t2>0?"+":"")+t2)}
  e2("line",{x1:X2(0),x2:X2(0),y1:10,y2:14+rh2*S.length,stroke:"var(--ink-3)"});
  e2("text",{x:(L2+W-R2)/2,y:52+rh2*S.length,"text-anchor":"middle"},"change in agreement, own answer vs no reference (points)");
  S.forEach(function(r,i){var y=14+rh2*i;
    e2("text",{class:"lab",x:L2-14,y:y+rh2/2+4,"text-anchor":"end"},r.name);
    [["solved",r.solved,"var(--c1)",y+8,r.n_solved],["failed",r.failed,"var(--c2)",y+rh2/2+1,r.n_failed]].forEach(function(b){
      var x0=X2(Math.min(0,b[1])), w=Math.abs(X2(b[1])-X2(0));
      var rect=e2("rect",{x:x0,y:b[3],width:Math.max(w,1),height:rh2/2-9,fill:b[2],rx:3});
      hov(rect,r.name+", own answer "+b[0]+" ("+b[4]+" responses): "+(b[1]>0?"+":"")+b[1].toFixed(1)+" points");
      e2("text",{class:"val",x:b[1]<0?x0-6:X2(b[1])+6,y:b[3]+rh2/2-13,"text-anchor":b[1]<0?"end":"start"},(b[1]>0?"+":"")+b[1].toFixed(1))});
  });

  // 3. peer minus none, by whether gpt-oss-120b's answer was right
  var P=D.peer, s3=document.getElementById("g3");
  if(!P||!s3)return;
  var e3=mk(s3), rh3=46, lo3=-30, hi3=20;
  var X3=function(v){return L2+(W-L2-R2)*(v-lo3)/(hi3-lo3)};
  var H3=20+rh3*P.length+50; s3.setAttribute("viewBox","0 0 900 "+H3);
  for(var t3=lo3;t3<=hi3;t3+=10){e3("line",{class:"gl",x1:X3(t3),x2:X3(t3),y1:10,y2:14+rh3*P.length});e3("text",{x:X3(t3),y:32+rh3*P.length,"text-anchor":"middle"},(t3>0?"+":"")+t3)}
  e3("line",{x1:X3(0),x2:X3(0),y1:10,y2:14+rh3*P.length,stroke:"var(--ink-3)"});
  e3("text",{x:(L2+W-R2)/2,y:52+rh3*P.length,"text-anchor":"middle"},"change in agreement, gpt-oss-120b's answer vs no reference (points)");
  P.forEach(function(r,i){var y=14+rh3*i;
    e3("text",{class:"lab",x:L2-14,y:y+rh3/2+4,"text-anchor":"end"},r.name);
    [["right",r.ok,"var(--c3)",y+8],["wrong",r.bad,"var(--c2)",y+rh3/2+1]].forEach(function(b){
      var x0=X3(Math.min(0,b[1])), w=Math.abs(X3(b[1])-X3(0));
      var rect=e3("rect",{x:x0,y:b[3],width:Math.max(w,1),height:rh3/2-9,fill:b[2],rx:3});
      hov(rect,r.name+", reference "+b[0]+": "+(b[1]>0?"+":"")+b[1].toFixed(1)+" points");
      e3("text",{class:"val",x:b[1]<0?x0-6:X3(b[1])+6,y:b[3]+rh3/2-13,"text-anchor":b[1]<0?"end":"start"},(b[1]>0?"+":"")+b[1].toFixed(1))});
  });
})();
"""


def main():
    M = json.loads((HERE / "results/metrics.json").read_text())
    H, SP, PE = M["headline"], M["split"], M.get("peer")
    if PE and len(PE) < len(H):  # show the peer arm only once every judge has finished it
        PE = None
    order = sorted(H, key=lambda j: -H[j]["none"])
    arms = []
    for j in order:
        h = H[j]
        r = dict(name=NAME[j], none=100 * h["none"], self=100 * h["self"], human=100 * h["human"])
        if PE and j in PE:
            r["peer"] = 100 * PE[j]["peer"]
        arms.append(r)
    split = [dict(name=NAME[j], solved=100 * SP[j][3], failed=100 * SP[j][7], n_solved=SP[j][0], n_failed=SP[j][4]) for j in order]
    mean_self = sum(H[j]["diff"] for j in H) / len(H)
    mean_hum = sum(H[j]["human"] - H[j]["none"] for j in H) / len(H)
    oss_fail = [SP[j][7] for j in ("gpt-oss-120b", "gpt-oss-20b")]
    peer, peer_line = None, ""
    if PE:
        key = "by_ref_deepseek-v3.1"
        peer = [dict(name=NAME[j], ok=100 * (PE[j][key]["ok_peer"] - PE[j][key]["ok_none"]),
                     bad=100 * (PE[j][key]["bad_peer"] - PE[j][key]["bad_none"])) for j in order if j in PE and key in PE[j]]
        mean_peer = sum(PE[j]["diff"] for j in PE) / len(PE)
        ok = sum(p["ok"] for p in peer) / len(peer)
        bad = sum(p["bad"] for p in peer) / len(peer)
        peer_line = (f"<li><b>A strong model's answer helps only when it is right: {ok:+.1f} points when gpt-oss-120b was right, "
                     f"{bad:+.1f} when it was wrong.</b><span>Averaged over judges, grading against gpt-oss-120b's answer changes "
                     f"agreement by {100*mean_peer:+.1f} points. A wrong reference pulls judges along with it.</span></li>")
    concl = (
        f"<li><b>Grading against your own answer doesn't help on average ({100*mean_self:+.1f} points over 8 judges).</b>"
        "<span>It helps three thinking-off judges (Nemotron-Super +4.6, Qwen3.5-9B +2.9, DeepSeek +2.5) and hurts gpt-oss-20b (−5.3) "
        "and Nemotron-Nano (−3.3).</span></li>"
        f"<li><b>When a judge's own answer is wrong, the reasoning judges follow it: {100*oss_fail[0]:+.1f} and {100*oss_fail[1]:+.1f} points.</b>"
        "<span>gpt-oss-120b and gpt-oss-20b gain little when their answer is right. Some thinking-off judges still gain when "
        "theirs is wrong, so writing an answer first may just make them read more carefully.</span></li>"
        + peer_line +
        f"<li><b>A correct reference is what matters: the expert answer lifts every judge, by {100*mean_hum:+.1f} points on average.</b>"
        "<span>Nemotron-Super goes from 71.3% to 87.5%, past gpt-oss-120b without a reference (80.2%).</span></li>")
    peer_fig = ('<section class="fig" aria-labelledby="f3"><h2 id="f3">A borrowed answer helps when it is right and hurts more when it is wrong</h2>'
                '<p class="take">Every judge grades against gpt-oss-120b\'s answer. Bars split responses by whether that answer was right '
                '(graded by DeepSeek-V3.1 with the expert reference).</p>'
                '<div class="chart"><svg id="g3" viewBox="0 0 900 450" role="img" aria-label="Change in agreement when grading against gpt-oss-120b\'s answer, '
                'split by whether that answer was right."></svg></div>'
                '<div class="legend"><span><i class="sq" style="background:var(--c3)"></i>gpt-oss-120b\'s answer right</span>'
                '<span><i class="sq" style="background:var(--c2)"></i>gpt-oss-120b\'s answer wrong</span></div></section>') if peer else (
                '<section class="fig"><h2>A borrowed answer from gpt-oss-120b</h2><div class="pending">The peer arm is still running. '
                'This chart fills in when every judge has graded against gpt-oss-120b\'s answer.</div></section>')
    data = dict(arms=arms, split=split, peer=peer)
    page = f"""<title>Solve Then Judge</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header>
  <div class="eyebrow">AC 297r · Dynamic LLM Juries · BFF-Bench</div>
  <h1>Should a judge answer the question before grading it?</h1>
  <p class="meta">Benchmark tested: BFF-Bench (80 two-turn finance conversations, 808 responses with a 2-of-3 human label) · 8 LLM judges · {'4' if peer else '3'} reference conditions</p>
</header>
<section class="fig" aria-labelledby="f1">
  <h2 id="f1">The expert reference lifts every judge; the judge's own answer does not</h2>
  <p class="take">Agreement with the human label for each judge, by what it grades against. Open circle = no reference.</p>
  <div class="chart"><svg id="g1" viewBox="0 0 900 400" role="img" aria-label="Dot plot of agreement per judge under each reference condition."></svg></div>
  <div class="legend"><span><i class="ring"></i>no reference</span><span><i style="background:var(--c2)"></i>its own answer</span>{'<span><i style="background:var(--c1)"></i>gpt-oss-120b&#39;s answer</span>' if peer else ''}<span><i style="background:var(--c3)"></i>expert reference</span></div>
</section>
<section class="fig" aria-labelledby="f2">
  <h2 id="f2">A wrong own answer drags the reasoning judges down; a right one adds little</h2>
  <p class="take">Change from grading against its own answer instead of nothing, split by whether that answer was right. Right / wrong comes from two graders with the expert reference (both must agree; DeepSeek alone for the gpt-oss judges).</p>
  <div class="chart"><svg id="g2" viewBox="0 0 900 450" role="img" aria-label="Change in agreement from self-reference, split by whether the judge's own answer was right."></svg></div>
  <div class="legend"><span><i class="sq" style="background:var(--c1)"></i>own answer right</span><span><i class="sq" style="background:var(--c2)"></i>own answer wrong</span></div>
</section>
{peer_fig}
<div class="next"><b>What this means for the router</b><ul>
  <li>Don't ask the judge to answer first by default. Give it a reference only when that reference is likely right.</li>
  <li>The disagreement trigger already flags items where judges are unsure; those are the ones worth a strong model's answer or an expert check.</li>
</ul></div>
<p class="note">Prior result: No Free Labels ran the same no-reference / own-answer / expert-reference comparison with five 2024 judges (GPT-4o, Llama 3.3 70B, Phi-4, Yi 1.5 34B, Qwen 2.5 7B), pooled over BFF-Bench and (C)MT-Bench with 5 votes per verdict. There, the own answer raised κ for four of five judges (e.g. GPT-4o 0.47 → 0.52) and the expert reference raised it most (GPT-4o 0.68). Here the own answer helps the thinking-off judges but not the always-reasoning gpt-oss judges, which already solve the question while grading.</p>
<p class="note">10/19 runs: one sample per judge at temperature 0.7, max 4,096 tokens, 2-of-3 human labels. Own answers come from the same model with thinking off where that can be switched off. Right / wrong labels for those answers are LLM grades against the expert reference (the two graders agree on 82%). Code: experiments/solve_then_judge on branch wip/cross-benchmark-analysis in keyuwww/dynamic-llm-juries.</p>
</div>
<div id="tip" role="status" aria-live="polite"></div>
<script type="application/json" id="data">{json.dumps(data)}</script>
<script>{JS}</script>
"""
    (HERE / "results/report.html").write_text(page)
    print("wrote", HERE / "results/report.html")


if __name__ == "__main__":
    main()
