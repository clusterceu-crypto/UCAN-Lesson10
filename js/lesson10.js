(function(){'use strict';
const C=window.UCAN_L10_CONFIG,S=window.UCANShared;if(!C||!S){document.body.innerHTML='<main><h1>Не вдалося завантажити конфігурацію заняття.</h1></main>';return}
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>Array.from(r.querySelectorAll(s)),store=S.createStorage(C.storageNamespace),globalStatus=$('#global-status');
const state={nav:store.get('navigation',{route:C.routes[0].id}),formative:store.get('formative',{selected:null,checked:false,correct:false}),portfolio:store.get('portfolio',{values:{},savedAt:null}),assessment:store.get('assessment',{answers:{},score:null,passed:false,checked:false}),completion:store.get('completion',{complete:false})};
const persist=p=>store.set(p,state[p]),routeIndex=id=>Math.max(0,C.routes.findIndex(r=>r.id===id)),routeAccessible=r=>!r.gatedBy||!!state.assessment.passed;
function announce(m){globalStatus.textContent='';requestAnimationFrame(()=>globalStatus.textContent=m)}
let termPopover=null,activeTermTrigger=null,activeTermKey=null,activeTermLabel=null,termParentContext=null;
function ensureTermPopover(){
  if(termPopover)return termPopover;
  const pop=document.createElement('div');
  pop.id='term-note-popover';pop.className='term-popover';pop.hidden=true;pop.setAttribute('role','note');pop.setAttribute('aria-live','polite');
  pop.innerHTML='<div class="term-popover-head"><strong class="term-popover-title" id="term-note-title"></strong><button class="term-popover-close" type="button" aria-label="Закрити пояснення">×</button></div><div class="term-popover-body" id="term-note-body"></div>';
  document.body.append(pop);termPopover=pop;
  $('.term-popover-close',pop).addEventListener('click',()=>closeTermNote(true));
  pop.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();if(termParentContext)restoreParentTerm();else closeTermNote(true)}});
  return pop
}
function resetExpanded(except=null){$$('.term-trigger[aria-expanded="true"]').forEach(b=>{if(b!==except)b.setAttribute('aria-expanded','false')})}
function positionTermPopover(trigger){
  const pop=ensureTermPopover();if(pop.hidden||!trigger||!trigger.isConnected)return;
  if(matchMedia('(max-width: 680px)').matches){pop.style.left='';pop.style.top='';pop.style.right='';return}
  pop.style.right='auto';pop.style.left='12px';pop.style.top='12px';
  const tr=trigger.getBoundingClientRect(),pr=pop.getBoundingClientRect(),gap=10,pad=12;
  let left=Math.min(Math.max(tr.left,pad),Math.max(pad,innerWidth-pr.width-pad));
  let top=tr.bottom+gap;if(top+pr.height>innerHeight-pad)top=Math.max(pad,tr.top-pr.height-gap);
  pop.style.left=`${Math.round(left)}px`;pop.style.top=`${Math.round(top)}px`;
}
function buildTermDefinition(key){
  const item=C.terms[key],body=document.createDocumentFragment();
  if(!item.nestedTerms||!item.nestedTerms.length){body.append(document.createTextNode(item.definition));return body}
  let rest=item.definition;
  item.nestedTerms.forEach(n=>{const i=rest.indexOf(n.phrase);if(i<0)return;body.append(document.createTextNode(rest.slice(0,i)));const nested=document.createElement('span');nested.className='term-inline';nested.dataset.term=n.key;nested.dataset.label=n.phrase;body.append(nested);createTermControl(nested,n.key,n.phrase,true);rest=rest.slice(i+n.phrase.length)});
  body.append(document.createTextNode(rest));return body
}
function renderTermPopover(key,label,trigger,nested=false){
  const pop=ensureTermPopover(),item=C.terms[key];if(!item)return;
  $('#term-note-title',pop).textContent=item.term;const body=$('#term-note-body',pop);body.replaceChildren(buildTermDefinition(key));
  pop.dataset.nested=String(!!nested);pop.hidden=false;activeTermTrigger=trigger;activeTermKey=key;activeTermLabel=label;
  resetExpanded(trigger);if(trigger&&trigger.isConnected)trigger.setAttribute('aria-expanded','true');else if(nested&&termParentContext&&termParentContext.trigger&&termParentContext.trigger.isConnected)termParentContext.trigger.setAttribute('aria-expanded','true');
  requestAnimationFrame(()=>positionTermPopover(trigger&&trigger.isConnected?trigger:(termParentContext&&termParentContext.trigger)))
}
function openTermNote(trigger,key,label,nested=false){
  if(activeTermTrigger===trigger&&!ensureTermPopover().hidden){if(termParentContext)restoreParentTerm();else closeTermNote(false);return}
  if(nested&&activeTermKey){termParentContext={key:activeTermKey,label:activeTermLabel,trigger:activeTermTrigger};if(activeTermTrigger&&activeTermTrigger.isConnected)activeTermTrigger.setAttribute('aria-expanded','true')}
  else{termParentContext=null;resetExpanded()}
  renderTermPopover(key,label,trigger,nested)
}
function closeTermNote(returnFocus=false){
  const pop=ensureTermPopover(),trigger=activeTermTrigger,parent=termParentContext&&termParentContext.trigger;
  resetExpanded();pop.hidden=true;pop.removeAttribute('data-nested');termParentContext=null;activeTermTrigger=null;activeTermKey=null;activeTermLabel=null;
  if(returnFocus){const target=trigger&&trigger.isConnected?trigger:(parent&&parent.isConnected?parent:null);if(target)target.focus()}
}
function restoreParentTerm(){
  if(!termParentContext){closeTermNote(true);return}
  const ctx=termParentContext;termParentContext=null;renderTermPopover(ctx.key,ctx.label,ctx.trigger,false);
  requestAnimationFrame(()=>{const nested=$('.term-trigger[data-term="machine-readable"]',ensureTermPopover());if(nested)nested.focus();else if(ctx.trigger&&ctx.trigger.isConnected)ctx.trigger.focus()})
}
function createTermControl(host,key,labelOverride,nested=false){
  if(!host||host.dataset.rendered==='true')return;const item=C.terms[key];if(!item)return;
  const label=labelOverride||host.dataset.label||item.term;host.dataset.rendered='true';host.textContent='';
  const b=document.createElement('button'),text=document.createElement('span'),info=document.createElement('span');
  b.type='button';b.className='term-trigger';b.dataset.term=key;b.dataset.nested=String(!!nested);b.setAttribute('aria-label',`${label}. Пояснення терміна`);b.setAttribute('aria-expanded','false');b.setAttribute('aria-controls','term-note-popover');
  text.className='term-text';text.textContent=label;info.className='term-info';info.setAttribute('aria-hidden','true');info.textContent='ⓘ';b.append(text,info);
  b.addEventListener('click',()=>openTermNote(b,key,label,nested));
  b.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();e.stopPropagation();openTermNote(b,key,label,nested);return}if(e.key==='Escape'&&b.getAttribute('aria-expanded')==='true'){e.preventDefault();e.stopPropagation();if(termParentContext)restoreParentTerm();else closeTermNote(false)}});
  host.append(b)
}
function renderTerms(){$$('.term-inline').forEach(host=>createTermControl(host,host.dataset.term,host.dataset.label,false));ensureTermPopover()}
document.addEventListener('pointerdown',e=>{if(!termPopover||termPopover.hidden)return;const t=e.target;if(termPopover.contains(t)||t.closest?.('.term-trigger'))return;closeTermNote(false)},true);
window.addEventListener('resize',()=>activeTermTrigger&&positionTermPopover(activeTermTrigger));
document.addEventListener('scroll',()=>activeTermTrigger&&positionTermPopover(activeTermTrigger),true);
function renderRoutes(){const strip=$('#route-strip');strip.innerHTML='';C.routes.forEach(r=>{const b=document.createElement('button');b.type='button';b.className='route-button';b.textContent=r.label;b.dataset.route=r.id;b.disabled=!routeAccessible(r);b.onclick=()=>showRoute(r.id,true);strip.append(b)})}
function updateNav(){const i=routeIndex(state.nav.route),r=C.routes[i];$('#lesson-label').textContent=C.currentLessonLabel;$('#page-label').textContent=r.label;$('#nav-position').textContent=`Розділ ${i+1} з ${C.routes.length}`;$$('.route-button').forEach(b=>{const x=C.routes.find(r=>r.id===b.dataset.route);b.disabled=!routeAccessible(x);b.toggleAttribute('aria-current',b.dataset.route===r.id);if(b.dataset.route===r.id)b.setAttribute('aria-current','page')});const prev=$('#nav-prev'),next=$('#nav-next');prev.disabled=i===0;prev.onclick=()=>i>0&&showRoute(C.routes[i-1].id,true);if(i===C.routes.length-1){next.textContent='Наступне заняття →';next.disabled=!C.nextLessonUrl;next.onclick=()=>{if(C.nextLessonUrl)location.href=C.nextLessonUrl;else announce('Маршрут наступного заняття поки не налаштований.')}}else{next.textContent='Далі →';const target=C.routes[i+1];next.disabled=!routeAccessible(target);next.onclick=()=>routeAccessible(target)?showRoute(target.id,true):announce('Завершення стане доступним після результату 5/5.')}const p=state.completion.complete?100:Math.round((i/(C.routes.length-1))*90);$('#lesson-progress').value=p;$('#progress-text').textContent=`Прогрес проходження: ${p}%`}
function showRoute(id,focus=false){if(termPopover&&!termPopover.hidden)closeTermNote(false);let i=routeIndex(id),r=C.routes[i];if(!routeAccessible(r)){i=routeIndex('assessment');r=C.routes[i]}$$('.lesson-page').forEach(p=>p.hidden=p.dataset.route!==r.id);state.nav.route=r.id;persist('nav');updateNav();if(focus){const h=$('h1',$(`.lesson-page[data-route="${r.id}"]`));if(h){h.tabIndex=-1;h.focus({preventScroll:true});h.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})}}}
function renderPortfolio(){const c=$('#portfolio-fields');c.innerHTML='';C.portfolio.fields.forEach((f,i)=>{const w=document.createElement('div'),l=document.createElement('label'),h=document.createElement('span'),t=document.createElement('textarea'),id=`portfolio-${f.id}`;w.className='portfolio-field';l.htmlFor=id;l.textContent=`${i+1}. ${f.label}`;h.className='helper';h.id=`${id}-helper`;h.textContent=f.helper;t.id=id;t.name=f.id;t.required=f.required;t.setAttribute('aria-describedby',h.id);t.value=state.portfolio.values[f.id]||'';t.addEventListener('input',()=>{state.portfolio.values[f.id]=t.value;persist('portfolio');t.removeAttribute('aria-invalid')});w.append(l,h,t);c.append(w)})}
function validatePortfolio(){const miss=[];C.portfolio.fields.forEach(f=>{const t=$(`#portfolio-${f.id}`),bad=f.required&&!t.value.trim();if(bad){miss.push({f,t});t.setAttribute('aria-invalid','true')}else t.removeAttribute('aria-invalid')});const e=$('#portfolio-errors');if(miss.length){e.hidden=false;e.innerHTML=`<strong>Заповніть усі п’ять полів.</strong><ul>${miss.map(x=>`<li>${x.f.label}</li>`).join('')}</ul>`;e.focus();return false}e.hidden=true;e.textContent='';return true}
function savePortfolio(e){e.preventDefault();if(!validatePortfolio())return;C.portfolio.fields.forEach(f=>state.portfolio.values[f.id]=$(`#portfolio-${f.id}`).value);state.portfolio.savedAt=new Date().toISOString();persist('portfolio');S.setStatus($('#portfolio-status'),'Міні-карту збережено в цьому браузері.','success');announce('Міні-карту збережено.')}
function pdf(){if(!validatePortfolio()){S.setStatus($('#portfolio-status'),'PDF не створено: спочатку заповніть усі п’ять полів.','error');return}try{const v={};C.portfolio.fields.forEach(f=>v[f.id]=$(`#portfolio-${f.id}`).value);S.setStatus($('#portfolio-status'),'Створюємо PDF…');const b=S.generatePortfolioPdf(C.portfolio,v);S.downloadBlob(new Blob([b],{type:'application/pdf'}),C.portfolio.filename);S.setStatus($('#portfolio-status'),'PDF створено локально. Дані нікуди не передавалися.','success');announce('PDF створено локально.')}catch(e){console.error(e);S.setStatus($('#portfolio-status'),'Не вдалося створити PDF. Ваші дані збережені в браузері.','error')}}
function renderResources(){const list=$('#resource-list');list.innerHTML='';C.resources.forEach(r=>{const a=document.createElement('article'),h=document.createElement('h2'),p=document.createElement('p'),l=document.createElement('a');a.className='resource-card';h.textContent=r.name;p.textContent=r.why;l.href=r.url;l.target='_blank';l.rel='noopener noreferrer';l.textContent=r.label;a.append(h,p,l);list.append(a)})}
function restoreFormative(){if(state.formative.selected){const i=$(`#formative-form input[value="${state.formative.selected}"]`);if(i)i.checked=true}if(state.formative.checked)S.setStatus($('#formative-feedback'),state.formative.correct?C.formative.feedbackCorrect:C.formative.feedbackRetry,state.formative.correct?'success':'error')}
function checkFormative(e){e.preventDefault();const q=$('#formative-form input[name="formative"]:checked');if(!q){S.setStatus($('#formative-feedback'),'Оберіть один варіант відповіді.','error');return}state.formative={selected:q.value,checked:true,correct:q.value===C.formative.correct};persist('formative');S.setStatus($('#formative-feedback'),state.formative.correct?C.formative.feedbackCorrect:C.formative.feedbackRetry,state.formative.correct?'success':'error')}
function restoreAssessment(){Object.entries(state.assessment.answers||{}).forEach(([q,v])=>{const i=$(`#assessment-form input[name="${q}"][value="${v}"]`);if(i)i.checked=true});if(state.assessment.checked)S.setStatus($('#assessment-feedback'),state.assessment.passed?'Результат 5/5. Завершення заняття доступне.':`Результат ${state.assessment.score||0}/5. Перегляньте відповіді та спробуйте ще раз.`,state.assessment.passed?'success':'error')}
function assessmentChange(e){if(!e.target.matches('input[type="radio"]'))return;state.assessment.answers[e.target.name]=e.target.value;if(state.assessment.passed||state.completion.complete){state.assessment.passed=false;state.assessment.checked=false;state.assessment.score=null;state.completion.complete=false;persist('completion');S.setStatus($('#assessment-feedback'),'Відповідь змінено. Перевірте всі відповіді повторно, щоб відновити завершення.','error');announce('Завершення знову заблоковано до повторної перевірки 5/5.')}persist('assessment');updateNav()}
function checkAssessment(e){e.preventDefault();const answers={};let full=true;Object.keys(C.assessment.answers).forEach(q=>{const i=$(`#assessment-form input[name="${q}"]:checked`);if(!i)full=false;else answers[q]=i.value});state.assessment.answers=answers;if(!full){state.assessment.checked=false;state.assessment.passed=false;state.assessment.score=null;state.completion.complete=false;persist('assessment');persist('completion');updateNav();S.setStatus($('#assessment-feedback'),'Дайте відповідь на всі п’ять запитань.','error');return}let score=0;Object.entries(C.assessment.answers).forEach(([q,a])=>{if(answers[q]===a)score++});state.assessment.score=score;state.assessment.checked=true;state.assessment.passed=score===C.assessment.passScore;state.completion.complete=state.assessment.passed;persist('assessment');persist('completion');updateNav();S.setStatus($('#assessment-feedback'),state.assessment.passed?'Результат 5/5. Завершення заняття доступне.':`Результат ${score}/5. Перегляньте відповіді та спробуйте ще раз.`,state.assessment.passed?'success':'error');announce(`Підсумкова перевірка: ${score} з 5.`)}
function resetLearning(){state.nav={route:C.routes[0].id};state.formative={selected:null,checked:false,correct:false};state.assessment={answers:{},score:null,passed:false,checked:false};state.completion={complete:false};['navigation','formative','assessment','completion'].forEach(p=>store.remove(p));$('#formative-form').reset();$('#assessment-form').reset();S.setStatus($('#formative-feedback'),'');S.setStatus($('#assessment-feedback'),'');showRoute('start',true);announce('Прогрес, практика й підсумкова перевірка очищені. Міні-карта збережена.')}
function clearPortfolio(){state.portfolio={values:{},savedAt:null};store.remove('portfolio');$$('#portfolio-form textarea').forEach(t=>{t.value='';t.removeAttribute('aria-invalid')});$('#portfolio-errors').hidden=true;S.setStatus($('#portfolio-status'),'Міні-карту видалено з цього браузера.','success');announce('Міні-карту видалено.')}
function bindDialogs(){const r=$('#reset-dialog'),c=$('#portfolio-clear-dialog');$('#reset-open').onclick=()=>r.showModal();r.addEventListener('close',()=>{if(r.returnValue==='confirm')resetLearning()});$('#portfolio-clear-open').onclick=()=>c.showModal();c.addEventListener('close',()=>{if(c.returnValue==='confirm')clearPortfolio()})}
function init(){renderTerms();renderRoutes();renderPortfolio();renderResources();restoreFormative();restoreAssessment();bindDialogs();$('#formative-form').addEventListener('submit',checkFormative);$('#portfolio-form').addEventListener('submit',savePortfolio);$('#pdf-download').onclick=pdf;$('#assessment-form').addEventListener('submit',checkAssessment);$('#assessment-form').addEventListener('change',assessmentChange);showRoute(state.nav.route,false);window.UCAN_TEST=Object.freeze({config:C,state,showRoute,validatePortfolio,storageKeys:()=>store.keys(),routeAccessible,generatePdfBytes:(long=false)=>{const v={};C.portfolio.fields.forEach(f=>v[f.id]=long?'Довгий тестовий український текст для перевірки перенесення, пагінації та відсутності обрізання. '.repeat(60):(state.portfolio.values[f.id]||'Тестове значення'));return S.generatePortfolioPdf(C.portfolio,v)}})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
