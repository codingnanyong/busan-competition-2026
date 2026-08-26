// Score-gated policy recommendation cards.
function triggeredMetricLine(code,categoryKey,fallback){
 const hits=(indicators[code][categoryKey]||[]).filter(m=>m.triggered);
 return hits.length?hits.map(m=>`${m.label} 취약 백분위 ${m.percentile}`).join(' · ')
  :fallback;}
function siblingCandidates(code,exceptCategory){
 return children[majorCategory].filter(c=>c.category!==exceptCategory).map(c=>{
  const item=assessments[code][c.category];
  return {label:c.label,score:item.score,candidate:item.status==='candidate_after_validation'};
 }).filter(item=>item.candidate);}
function policyHtml(name,code,child){const policy=policies[child.category];
 const a=assessments[code][child.category];
 const evidence=triggeredMetricLine(code,child.category,a.triggers);
 if(a.status!=='candidate_after_validation'){
  const stance=a.score<30?'low':'monitor';
  const stanceLabel=a.score<30?'상대 저취약':'모니터링';
  const others=siblingCandidates(code,child.category);
  const otherHtml=others.length
   ?`<p>같은 생활여건 영역에서 70점 이상인 세부 항목:
   ${others.map(item=>`${item.label} ${item.score.toFixed(1)}`).join(' · ')}.
   트리에서 해당 항목을 선택하면 이 동에 맞는 정책 수단이 열립니다.</p>`
   :`<p>같은 생활여건 영역에서도 70점 이상 세부 항목이 없습니다. 다른 영역을 함께
   확인하세요.</p>`;
  const watch=(indicators[code][child.category]||[]).filter(m=>m.triggered);
  const watchHtml=watch.length
   ?`<p>세부 지표 중 70점 이상은 있습니다:
   ${watch.map(m=>`${m.label} ${m.percentile}`).join(' · ')}.
   항목 종합점수는 임계값 미만이므로 정책 패키지 적용은 보류합니다.</p>`:'';
  return `<div class="policy ${stance}"><b>이 동의 분포에 따른 정책 판단</b>
 <h2>${name} · ${child.label}</h2>
 <h3>${stanceLabel} · ${a.score.toFixed(1)}점</h3>
 <p>부산 206개 동 분포에서 이 항목은 정책검토 임계값 70점에 미달합니다.
 카탈로그의 「${policy.title}」은 고취약 동에 해당하는 수단이며 이 동에는 적용하지
 않습니다.</p>${watchHtml}${otherHtml}
 <p class="warning"><b>해석 제한</b><br>${policy.limit}</p></div>`;}
 return `<div class="policy"><b>조건부 정책 방향 · 검증 후 정책검토 후보</b>
 <h2>${name} · ${child.label} ${a.score.toFixed(1)}점</h2><h3>${policy.title}</h3>
 <p>주관: ${policy.lead}</p><div class="policy-grid">
 <div class="policy-item"><b>이 동이 넘은 임계값</b>세부 점수 ${a.score.toFixed(1)}
 (70점 이상) · ${evidence}</div>
 <div class="policy-item"><b>분석이 포착한 신호</b>${policy.signal}</div>
 <div class="policy-item"><b>우선 확인 대상</b>${name}에서 ${policy.target}</div></div>
 <div class="policy-item"><b>실행 순서</b>${policy.steps}</div>
 <p><b>적용 예시</b><br>${name} ${a.score.toFixed(1)}점을 근거로 대상지만 선별합니다.
 ${policy.example}</p>
 <p><b>성과지표</b><br>${policy.monitor}</p>
 <div class="policy-case"><b>정책 설계 참고사례</b><br>${policy.case}<br>
 <a href="${policy.case_url}" target="_blank" rel="noopener noreferrer">공식 자료 보기 ↗</a>
 <p class="scores">이 분석에 적용할 때: ${policy.case_note}</p></div>
 <p class="warning"><b>해석 제한</b><br>${policy.limit}</p></div>`;}
function emptyPolicy(name,code){if(!name)return `<h2>정책 방향을 보려면 행정동과 세부 항목을 선택하세요</h2>
<p>선택한 동의 점수 구간이 70점 이상일 때만 해당 항목의 정책 수단을 검토 후보로
보여줍니다. 모든 동에 같은 처방이 나가지 않습니다.</p>`;
 if(!code)return `<h2>${name} · 정책 방향</h2><p>트리에서 세부 평가항목을 선택하면
 이 동의 점수 구간에 맞는 정책 판단이 나타납니다.</p>`;
 const rows=children[majorCategory].map(c=>{const a=assessments[code][c.category];
  return {label:c.label,score:a.score,candidate:a.status==='candidate_after_validation'};});
 const hits=rows.filter(row=>row.candidate);
 const rest=rows.filter(row=>!row.candidate);
 const hitHtml=hits.length
  ?`<p>이 생활여건 영역에서 70점 이상인 세부 항목입니다. 항목을 선택하면 이 동에 맞는
  정책 수단이 열립니다.</p><ul>${hits.map(row=>`<li><b>${row.label}</b>
  ${row.score.toFixed(1)} · 검증 후 정책검토 후보</li>`).join('')}</ul>`
  :`<p>이 생활여건 영역에서는 70점 이상 세부 항목이 없습니다. 지금은 모니터링이며
  카탈로그 정책 패키지를 이 동에 적용하지 않습니다.</p>`;
 const restHtml=rest.length
  ?`<p class="scores">모니터링: ${rest.map(row=>`${row.label} ${row.score.toFixed(1)}`)
  .join(' · ')}</p>`:'';
 return `<div class="policy ${hits.length?'':'monitor'}"><b>이 동의 분포에 따른 정책 판단</b>
 <h2>${name} · ${labels[majorCategory]}</h2>${hitHtml}${restHtml}</div>`;}
