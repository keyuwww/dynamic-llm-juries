/* Study B takeaways and the hypotheses table; numbers are read from D where they vary by model. */
(function(){
  const ms=Object.keys(D.probes);
  const get=(m,src,L)=>(D.probes[m].B3||[]).find(x=>x.labels===src&&x.level===L)||{};
  const rng=(vals)=>{const v=vals.filter(x=>x!=null);return v.length?`${f2(Math.min(...v))}–${f2(Math.max(...v))}`:"–"};
  const hiP=rng(ms.map(m=>get(m,"own","high").verdict)), hiB=rng(ms.map(m=>get(m,"own","high").baseline));
  const allP=rng(ms.map(m=>get(m,"own","all").verdict)), qP=rng(ms.map(m=>get(m,"own","all").q_end));
  const tP=rng(ms.map(m=>get(m,"tinker","high").verdict)), tB=rng(ms.map(m=>get(m,"tinker","high").baseline));
  const hw=rng(ms.map(m=>((D.probes[m].B4.cells||[]).find(c=>c.cell==="HW")||{}).mean));
  const mw=rng(ms.map(m=>((D.probes[m].B4.cells||[]).find(c=>c.cell==="MW")||{}).mean));
  const own=rng(ms.map(m=>((D.probes[m].B5||[]).find(x=>x.target==="own")||{}).auc));
  const oth=rng(ms.map(m=>{const o=(D.probes[m].B5||[]).filter(x=>x.target!=="own"&&x.target!=="same model, reasoning run"&&x.auc!=null);return o.length?o.reduce((s,x)=>s+x.auc,0)/o.length:null}));
  const set=(id,items)=>{const e=document.getElementById(id);if(e)e.innerHTML=items.map(t=>`<li>${t}</li>`).join("")};
  if(ms.length){
    set("take-b1",[`At <b class="k-hi">high confidence</b>, hidden states separate wrong from right at ${hiP}, only about 0.05 above text features (${hiB}); intervals overlap.`,
      `Pooled over levels the probes reach ${allP}, mostly by reading the confidence itself.`,
      `After the <b>question</b> alone they are at chance (${qP}): difficulty lives in the answer pair.`]);
    set("take-b2",[`Before any reasoning, hidden states don't predict the <b>reasoned</b> verdict's confident errors beyond text features (${tP} vs ${tB}).`]);
    set("take-b3",[`<b class="k-hi">Confident errors</b> sit at ${hw} on the axis from unsure-wrong (0) to confident-right (1): much closer to confident-right than intermediate errors (${mw}).`,
      `So they are <b>mostly believed</b>, with a little correctness information left at high confidence.`]);
    set("take-b4",[`A model's error probe predicts <b>other judges'</b> errors at ${oth}, against ${own} for its own: it mostly reads <b>item difficulty</b>.`]);
  }
  const H=[
    ["Confident errors are shared with other judges more than unsure errors","good","Supported",`Others also wrong in both orders: ${f2(A2("third").high.others_W_mean)} vs ${f2(A2("third").low.others_W_mean)} of 7 (null ≈ 1); holds under all three level schemes.`],
    ["Sharing is strongest within a model family","mixed","Weak","Lift 2.6–2.8× within family vs 2.4–2.5× across."],
    ["Confident errors sit on contested labels or near ties","good","Supported","Human split +0.63 SD vs right answers at high confidence; coders flag 65% of confident errors as label problems or ties."],
    ["The judge's own token probability reveals hidden doubt","bad","Not supported","Within-level AUROC 0.53–0.60; token probability is saturated."],
    ["Other judges catch confident errors","good","Supported","Others' doubt: 0.72 at high vs 0.59 at low confidence."],
    ["Hidden states separate wrong from right at the same confidence","mixed","Weak",ms.length?`High level ${hiP} vs text baseline ${hiB}.`:"pending"],
    ["Confident errors look like confident right answers inside the model","mixed","Mostly",ms.length?`Position ${hw} on the unsure-wrong → confident-right axis.`:"pending"],
    ["The signal exists before the answers are read","bad","Not supported",ms.length?`Question-only probes ${qP}.`:"pending"],
    ["The probe reads the model's own belief, not item difficulty","bad","Not supported",ms.length?`Others' errors ${oth} vs own ${own}.`:"pending"]];
  document.getElementById("hyp").innerHTML=H.map(([h,c,v,e])=>`<tr><td>${h}</td><td><span class="pill ${c}">${v}</span></td><td>${e}</td></tr>`).join("");
})();
