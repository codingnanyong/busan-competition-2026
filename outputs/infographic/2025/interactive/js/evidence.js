// Dong evidence, indicators, and reference layers.
function percentage(value){return `${Math.round(Number(value)*100)}%`;}
function accidentHtml(code){const summary=accidentSummary[code];return summary
 ?`<div class="accident-reference"><b>교통사고 다발지역 근거</b><br>
 2024년 선정 다발지역 ${summary.location_count}곳 · 사고 ${summary.occurrence_count}건 ·
 사상자 ${summary.casualty_count}명<br>선정 지점의 사고 발생 건수는 안전 영역에
 반영됩니다. 전체 사고 전수자료는 아닙니다.</div>`
 :`<div class="accident-reference"><b>교통사고 다발지역 근거</b><br>
 이 행정동에서는 2024년 선정 다발지점이 확인되지 않았습니다. 이는 사고가 없거나
 안전하다는 뜻이 아니며, 전체 사고자료 확인이 필요합니다.</div>`;}
function metricHtml(m){const disclosure=m.estimate_used
  ?`<div class="estimate"><b>⚠ 추정값 사용</b><br>방법: ${m.estimation_method}<br>
  사용 사유: ${m.estimation_reason}</div>`
  :'';return `<div class="metric">
 <div class="metric-head"><b>${m.label}</b><span>${m.raw}</span></div>
 <div class="scores">취약도 백분위 ${m.percentile} · 평가 반영 비율 ${percentage(m.weight)} ·
 자료 유형 ${m.value_status} · 자료 신뢰도 ${m.confidence}</div>${disclosure}
 <div class="bar"><i style="width:${m.percentile}%"></i></div>
 <div class="scores">원자료 한계: ${m.quality} ·
 기술 근거: ${m.evidence}</div></div>`;}
function referenceHtml(code,categoryKey){const items=referenceContext[code]?.[categoryKey]||[];
 if(!items.length)return '';return `<div class="reference-context"><h4>점수 제외 참고지표</h4>
 ${items.map(item=>`<div class="metric"><div class="metric-head"><b>${item.label}</b>
 <span>${item.value.toLocaleString()} ${item.unit}</span></div>
 <div class="scores">부산 내 값의 상대 위치 ${item.percentile} · ${item.note}</div>
 <div class="bar"><i style="width:${item.percentile}%"></i></div></div>`).join('')}</div>`;}
function compositionBlock(title,items,note){if(!items?.length)return '';
 return `<div class="reference-context">
 <h4>${title}</h4>${items.map(item=>`<div class="composition-row"><b>${item.label}</b>
 <div class="bar"><i style="width:${item.share}%"></i></div>
 <span>${item.share}%</span></div>`).join('')}
 <div class="scores">${note}</div></div>`;}
function compositionHtml(code,categoryKey){
 if(categoryKey!=='local_employment_opportunity')return '';
 const data=referenceCompositions[code]||{};
 return compositionBlock('생활인구 구성',data.living_population,
 '거주·직장·방문 생활인구의 구성비이며 점수에는 반영하지 않음')+
 compositionBlock('소비매출 상위 업종 구성',data.sales,
 '일평균 업종별 매출액 구성비 상위 5개이며 주민소득·고용 점수에는 반영하지 않음');}
function trafficTrendHtml(){if(!trafficTrend.length)return '';
 const max=Math.max(...trafficTrend.map(d=>d.accidents));
 return `<div class="reference-context"><h4>부산 교통사고 최근 5년 추이</h4>${trafficTrend.map(d=>
 `<div class="composition-row"><b>${d.year}</b><div class="bar">
 <i style="width:${d.accidents/max*100}%"></i></div>
 <span>${d.accidents.toLocaleString()}건</span></div>`).join('')}
 <div class="scores">도로교통공단 부산 전체 통계 · 행정동 점수에는 반영하지 않음</div></div>`;}
function childHtml(code,child){const a=assessments[code][child.category];
 const metrics=indicators[code][child.category]
  .map(metricHtml).join('');const gate=a.status==='candidate_after_validation'
  ?'<span class="trigger">검증 후 정책검토 후보</span>'
  :'<span class="badge">모니터링</span>';return `<section class="subcategory">
 <h3>${child.label} ${a.score.toFixed(1)}</h3>
 <p class="scores">영역 점수 반영 비율 ${percentage(child.weight)} ·
 자료 신뢰도 ${a.confidence} · ${gate}</p>
 <p class="scores">우선 점검 지표: ${a.triggers}</p>
 ${metrics}${referenceHtml(code,child.category)}
 ${compositionHtml(code,child.category)}</section>`;}
function childOverviewHtml(code,child){const a=assessments[code][child.category];return `
 <div class="child-overview"><span>${child.label} · 영역 점수 반영 비율
 ${percentage(child.weight)}</span><strong>${a.score.toFixed(1)}</strong>
 <span class="scores">자료 신뢰도 ${a.confidence} ·
 우선 점검 지표 ${a.triggers}</span></div>`;}
function show(e){const d=e.target.dataset;if(!d.name)return;selected=e.target;
 const major=majorAssessments[d.code][majorCategory];
 const gate=major.status==='candidate_after_validation'
  ?'<span class="trigger">현장 검증 후 정책 검토</span>'
  :'<span class="badge">모니터링</span>';
 const accidentEvidence=category==='traffic_accident_risk'?accidentHtml(d.code):'';
 const heading=`<h2>${d.name}</h2><p class="scores">${d.rank}</p>${accidentEvidence}`;
 if(category){const child=children[majorCategory].find(c=>c.category===category);
  detail.innerHTML=heading+`<p class="scores">소속 생활여건 영역 · ${labels[majorCategory]}
  ${major.score.toFixed(1)}</p>`+childHtml(d.code,child);
  policyPanel.innerHTML=policyHtml(d.name,d.code,child);return;}
 const childOverview=children[majorCategory].map(c=>childOverviewHtml(d.code,c)).join('');
 detail.innerHTML=heading+`<h3>${labels[majorCategory]} ${major.score.toFixed(1)}</h3>
 <p>종합 자료 신뢰도 <span class="badge">${major.confidence}</span>
 · ${gate}</p><p class="scores">70점 이상 우선 점검 항목:
 ${major.triggered_children}</p><p class="scores">세부 평가항목 점수에 표시된 반영 비율을
 적용해 합산한 결과입니다. 트리에서 세부 항목을 선택하면 평가에 사용한 지표가
 오른쪽에, 이 동의 점수 구간에 맞는 정책 판단이 하단에 열립니다.</p>${childOverview}
 ${referenceHtml(d.code,'major_'+majorCategory)}
 ${majorCategory==='safety'?trafficTrendHtml():''}`;
 policyPanel.innerHTML=emptyPolicy(d.name,d.code);
}
