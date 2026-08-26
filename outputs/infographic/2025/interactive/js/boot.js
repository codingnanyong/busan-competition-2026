// Event wiring and equal-height layout.
document.querySelectorAll('path').forEach(p=>{p.tabIndex=0;p.addEventListener('mouseenter',show);
p.addEventListener('click',show);p.addEventListener('focus',show);});
document.querySelectorAll('.tree-major').forEach(node=>node.addEventListener('click',()=>
 selectNode(node.dataset.majorCategory)));
document.querySelectorAll('.tree-child').forEach(node=>node.addEventListener('click',()=>{
 node.closest('details').open=true;selectNode(node.dataset.majorCategory,node.dataset.category);
}));
const compactLayout=window.matchMedia('(max-width:720px)');
const mapPanel=document.querySelector('.map');
const treePanel=document.querySelector('.category-tree');
function syncPanelHeights(){if(compactLayout.matches){detail.style.height='';
 treePanel.style.maxHeight='';return;}
 const height=mapPanel.offsetHeight;
 if(Math.abs((parseFloat(detail.style.height)||0)-height)<1
  &&Math.abs((parseFloat(treePanel.style.maxHeight)||0)-height)<1)return;
 detail.style.height=height+'px';treePanel.style.maxHeight=height+'px';}
new ResizeObserver(syncPanelHeights).observe(mapPanel);
compactLayout.addEventListener('change',syncPanelHeights);
selectNode(majorCategory);
