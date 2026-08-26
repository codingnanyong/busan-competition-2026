// Map coloring and category selection.
function color(score){const hue=48-score*.45;return `hsl(${hue} 88% ${62-score*.18}%)`;}
function scoreOf(path){return category
 ?assessments[path.dataset.code][category].score
 :majorAssessments[path.dataset.code][majorCategory].score;}
function selectNode(nextMajor,nextCategory=null){majorCategory=nextMajor;category=nextCategory;
 document.querySelectorAll('.tree-major').forEach(node=>node.classList.toggle('active',
  category===null&&node.dataset.majorCategory===majorCategory));
 document.querySelectorAll('.tree-child').forEach(node=>node.classList.toggle('active',
  node.dataset.category===category));
 const selectedLabel=category?categoryLabels[category]:labels[majorCategory];
 document.getElementById('map-title').textContent=selectedLabel+' 취약도 분포';
 const accidentSelected=category==='traffic_accident_risk';
 accidentControl.hidden=!accidentSelected;
 if(!accidentSelected){accidentLayer.hidden=true;accidentLayer.style.display='none';
  accidentToggle.setAttribute('aria-pressed','false');
  accidentToggle.textContent='교통사고 다발지역 표시';}
 const safetyOverview=majorCategory==='safety'&&category===null;
 safetyRiskControl.hidden=!safetyOverview;
 if(!safetyOverview){safetyRiskLayer.hidden=true;safetyRiskLayer.style.display='none';
  safetyRiskToggle.setAttribute('aria-pressed','false');
  safetyRiskToggle.textContent='생활안전 위험지역 표시';}
 const aedSelected=category==='healthcare_supply';aedControl.hidden=!aedSelected;
 if(!aedSelected){aedLayer.hidden=true;aedLayer.style.display='none';
  aedToggle.setAttribute('aria-pressed','false');aedToggle.textContent='AED 위치 표시';}
 const parkOverview=majorCategory==='environment'&&category===null;parkControl.hidden=!parkOverview;
 if(!parkOverview){parkLayer.hidden=true;parkLayer.style.display='none';
  parkToggle.setAttribute('aria-pressed','false');parkToggle.textContent='도시공원 위치 표시';}
 document.querySelectorAll('path').forEach(p=>p.style.fill=color(scoreOf(p)));
 if(selected)show({target:selected});
}
