from pathlib import Path
import subprocess,time,json,urllib.request,websocket,re,base64,sys
ROOT=Path(__file__).resolve().parents[1]
html=(ROOT/'index.html').read_text(encoding='utf-8')
css=(ROOT/'css/shared.css').read_text(encoding='utf-8')
config=(ROOT/'js/lesson10.config.js').read_text(encoding='utf-8')
shared=(ROOT/'js/shared.js').read_text(encoding='utf-8')
lesson=(ROOT/'js/lesson10.js').read_text(encoding='utf-8')
# Managed Chromium blocks local URL navigation in this environment. This is a bounded final learner-facing Pre-QA smoke only:
# inject the exact candidate document and exact local CSS/JS into about:blank without changing browser policy.
html=re.sub(r'<link href="css/shared\.css" rel="stylesheet"\s*/?>','<style>'+css+'</style>',html,count=1)
script_tag='<script src="js/lesson10.config.js"></script><script src="js/shared.js"></script><script src="js/lesson10.js"></script>'
shim=r'''<script>
window.__qaErrors=[];window.addEventListener('error',e=>window.__qaErrors.push(String(e.message||e.error||'error')));
(()=>{const m=new Map();const ls={getItem:k=>m.has(String(k))?m.get(String(k)):null,setItem:(k,v)=>m.set(String(k),String(v)),removeItem:k=>m.delete(String(k)),clear:()=>m.clear(),key:i=>Array.from(m.keys())[i]||null,get length(){return m.size}};Object.defineProperty(window,'localStorage',{value:ls,configurable:true});})();
</script>'''
if script_tag not in html: raise SystemExit('candidate script tag sequence not found')
html=html.replace(script_tag,shim+f'<script>{config}</script><script>{shared}</script><script>{lesson}</script>',1)
port=9267
proc=subprocess.Popen(['chromium','--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',f'--remote-debugging-port={port}','--remote-allow-origins=*','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
ws=None;events=[];seq=0;checks=[]
def ck(name,ok,detail=''): checks.append({'name':name,'pass':bool(ok),'detail':detail})
def call(method,params=None,timeout=10):
    global seq
    seq+=1;ident=seq;ws.send(json.dumps({'id':ident,'method':method,'params':params or {}}));end=time.time()+timeout
    while time.time()<end:
        msg=json.loads(ws.recv())
        if msg.get('id')==ident:return msg
        events.append(msg)
    raise TimeoutError(method)
def eval_js(expr):
    r=call('Runtime.evaluate',{'expression':expr,'returnByValue':True,'awaitPromise':True})
    if r.get('result',{}).get('exceptionDetails'):raise RuntimeError(r['result']['exceptionDetails'])
    return r.get('result',{}).get('result',{}).get('value')
def set_view(w,h):
    call('Emulation.setDeviceMetricsOverride',{'width':w,'height':h,'deviceScaleFactor':1,'mobile':w<=420})
    eval_js('window.dispatchEvent(new Event("resize")); true')
def show_route(r):return eval_js(f'window.UCAN_TEST.showRoute({json.dumps(r)},false); true')
def click_term(k):
    return eval_js(f'''(async()=>{{const b=document.querySelector(`.term-trigger[data-term="{k}"]`);if(!b)return {{ok:false}};b.scrollIntoView({{block:'center',behavior:'instant'}});const before=document.documentElement.scrollHeight;b.click();await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));const p=document.getElementById('term-note-popover'),q=p.getBoundingClientRect();return {{ok:!p.hidden,expanded:b.getAttribute('aria-expanded'),controls:b.getAttribute('aria-controls'),before,after:document.documentElement.scrollHeight,left:q.left,right:q.right,top:q.top,bottom:q.bottom,vw:innerWidth,vh:innerHeight,sw:document.documentElement.scrollWidth}}}})()''')
try:
    tabs=None
    for _ in range(80):
        try:tabs=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json',timeout=.5));break
        except Exception:time.sleep(.1)
    if not tabs:raise RuntimeError('Chromium DevTools endpoint unavailable')
    ws=websocket.create_connection(tabs[0]['webSocketDebuggerUrl'],timeout=10)
    call('Page.enable');call('Runtime.enable');call('Log.enable')
    ver=call('Browser.getVersion')['result']
    fid=call('Page.getFrameTree')['result']['frameTree']['frame']['id']
    set_view(1440,900)
    call('Page.setDocumentContent',{'frameId':fid,'html':html},timeout=15);time.sleep(.5)
    ready=eval_js('({routes:document.querySelectorAll(".route-button").length,terms:document.querySelectorAll(".term-trigger").length,portfolio:document.querySelectorAll(".portfolio-field").length,errors:window.__qaErrors.slice(),version:window.UCAN_TEST?.config?.packageVersion})')
    ck('candidate initialized',ready['routes']==10 and ready['terms']==14 and ready['portfolio']==5 and ready['version']=='1.7',str(ready))
    ck('initial runtime errors zero',not ready['errors'],str(ready['errors']))
    ck('zero term controls in headings',eval_js('document.querySelectorAll("h1 .term-trigger,h2 .term-trigger,h3 .term-trigger,h4 .term-trigger,h5 .term-trigger,h6 .term-trigger,.lesson-subtitle .term-trigger").length')==0)

    # Route integrity and sequence.
    route_results={}
    for r in ['start','open-data','principles','decision','wua','resources','portfolio','practice','assessment']:
        show_route(r);time.sleep(.03)
        route_results[r]=eval_js('({visible:document.querySelectorAll(".lesson-page:not([hidden])").length,current:document.querySelector(".lesson-page:not([hidden])")?.dataset.route||null,h1:document.querySelector(".lesson-page:not([hidden]) h1")?.textContent.trim()||null})')
    eval_js('window.UCAN_TEST.state.assessment.passed=true;window.UCAN_TEST.state.completion.complete=true;true')
    show_route('completion');time.sleep(.03)
    route_results['completion']=eval_js('({visible:document.querySelectorAll(".lesson-page:not([hidden])").length,current:document.querySelector(".lesson-page:not([hidden])")?.dataset.route||null,h1:document.querySelector(".lesson-page:not([hidden]) h1")?.textContent.trim()||null})')
    ck('all 10 routes render one-at-a-time',all(v['visible']==1 and v['current']==k and v['h1'] for k,v in route_results.items()),json.dumps(route_results,ensure_ascii=False))
    eval_js('window.UCAN_TEST.state.assessment.passed=false;window.UCAN_TEST.state.completion.complete=false;true')

    seqcheck=eval_js('''(()=>{const pages=[...document.querySelectorAll('.lesson-page')],idx=x=>pages.findIndex(p=>p.dataset.route===x),p=document.querySelector('.lesson-page[data-route="portfolio"]'),q=document.querySelector('.lesson-page[data-route="practice"]');const qkids=[...q.children];return {routeOrder:[idx('resources'),idx('portfolio'),idx('practice'),idx('assessment')],steps:p.querySelectorAll('.decision-stepper>li').length,cues:[...p.querySelectorAll('.example-line')].filter(x=>x.textContent.includes('У тому самому прикладі:')).length,bridge:!!p.querySelector('.formative-transition'),formative:qkids.indexOf(q.querySelector('#formative-form')),filled:qkids.indexOf(q.querySelector('.filled-card')),learner:qkids.indexOf(q.querySelector('#portfolio-form')),filledFields:q.querySelectorAll('.filled-card dl>div').length,portfolioFields:q.querySelectorAll('.portfolio-field').length,stages:[...q.querySelectorAll(':scope>h2')].map(x=>x.textContent.trim()),transfer:!!q.querySelector('.transfer-cue'),helsinkiParts:document.querySelectorAll('.helsinki-case .case-part').length,kyiv:!!document.querySelector('.kyiv-case'),kyivLink:document.querySelector('.kyiv-case a')?.href||'',wuaMastery:document.querySelector('.lesson-page[data-route="wua"]')?.textContent.includes('не потрібно вміти працювати з платформою WUA')||false,helsinkiCta:document.querySelector('.helsinki-case a')?.textContent.trim()||''}})()''')
    ck('corrected learner sequence/components',seqcheck['routeOrder']==[5,6,7,8] and seqcheck['steps']==5 and seqcheck['cues']==5 and seqcheck['bridge'] and 0<=seqcheck['formative']<seqcheck['filled']<seqcheck['learner'] and seqcheck['filledFields']==5 and seqcheck['portfolioFields']==5 and seqcheck['transfer'] and seqcheck['helsinkiParts']==5 and seqcheck['kyiv'] and 'data.kyivcity.gov.ua' in seqcheck['kyivLink'] and seqcheck['wuaMastery'] and seqcheck['helsinkiCta']=='Переглянути Helsinki Region Infoshare →',json.dumps(seqcheck,ensure_ascii=False))

    # Formative exact protected answer behavior, bounded check.
    show_route('practice');time.sleep(.03)
    formative=eval_js('''(()=>{const f=document.querySelector('#formative-form');const opts=[...f.querySelectorAll('input[name="formative"]')];return {opts:opts.map(x=>x.value),correct:window.UCAN_TEST.config.formative.correct,status:document.querySelectorAll('#formative-feedback').length}})()''')
    ck('formative contract retained',formative['opts']==['A','B','C','D'] and formative['correct']=='C' and formative['status']==1,json.dumps(formative,ensure_ascii=False))

    viewport_results={}
    for w,h in [(375,812),(768,900),(1440,900)]:
        set_view(w,h)
        per_routes={}
        eval_js('window.UCAN_TEST.state.assessment.passed=true;window.UCAN_TEST.state.completion.complete=true;true')
        for r in ['start','open-data','principles','decision','wua','resources','portfolio','practice','assessment','completion']:
            show_route(r);time.sleep(.025)
            per_routes[r]=eval_js('({sw:document.documentElement.scrollWidth,vw:innerWidth,visible:document.querySelectorAll(".lesson-page:not([hidden])").length})')
        eval_js('window.UCAN_TEST.state.assessment.passed=false;window.UCAN_TEST.state.completion.complete=false;true')
        # term popover fit/no flow shift
        show_route('open-data');time.sleep(.03);pop=click_term('open-data');time.sleep(.04)
        pop_ok=pop['ok'] and pop['expanded']=='true' and pop['controls']=='term-note-popover' and pop['before']==pop['after'] and pop['left']>=-1 and pop['right']<=pop['vw']+1 and pop['top']>=-1 and pop['bottom']<=pop['vh']+1 and pop['sw']<=pop['vw']+1
        eval_js('document.querySelector(`.term-trigger[data-term="open-data"]`).click();true')
        # key corrected route readability metrics
        show_route('portfolio');time.sleep(.04)
        worked=eval_js('''(()=>{const x=document.querySelector('.decision-stepper').getBoundingClientRect();return {left:x.left,right:x.right,vw:innerWidth,sw:document.documentElement.scrollWidth,steps:document.querySelectorAll('.decision-stepper>li').length}})()''')
        show_route('practice');time.sleep(.04)
        practice_m=eval_js('''(()=>{const f=document.querySelector('.filled-card').getBoundingClientRect(),p=document.querySelector('#portfolio-form').getBoundingClientRect();return {filledLeft:f.left,filledRight:f.right,formLeft:p.left,formRight:p.right,vw:innerWidth,sw:document.documentElement.scrollWidth,fields:document.querySelectorAll('.portfolio-field').length}})()''')
        show_route('wua');time.sleep(.04)
        city=eval_js('''(()=>{const h=document.querySelector('.helsinki-case').getBoundingClientRect(),k=document.querySelector('.kyiv-case').getBoundingClientRect(),route=document.querySelector('.lesson-page[data-route="wua"]');return {hLeft:h.left,hRight:h.right,kLeft:k.left,kRight:k.right,vw:innerWidth,sw:document.documentElement.scrollWidth,helsinkiParts:document.querySelectorAll('.helsinki-case .case-part').length,helsinkiCta:document.querySelector('.helsinki-case a')?.textContent.trim()||'',kyivTitle:document.querySelector('.kyiv-case h2')?.textContent.trim()||'',kyivLink:document.querySelector('.kyiv-case a')?.href||'',wuaRole:route.textContent.includes('Роль WUA в цьому занятті.'),wuaMastery:route.textContent.includes('не потрібно вміти працювати з платформою WUA')}})()''')
        eval_js('window.UCAN_TEST.state.assessment.passed=true;window.UCAN_TEST.state.completion.complete=true;true');show_route('completion');time.sleep(.04)
        completion=eval_js('''(()=>{const r=document.querySelector('.lesson-page[data-route="completion"]'),x=r.getBoundingClientRect();return {left:x.left,right:x.right,vw:innerWidth,sw:document.documentElement.scrollWidth,transfer:r.textContent.includes('візьміть завершену міні-карту на робочу розмову'),wua:r.textContent.includes('аналітичні ресурси на кшталт WUA'),responsibility:r.textContent.includes('відповідальністю міської команди')}})()''')
        eval_js('window.UCAN_TEST.state.assessment.passed=false;window.UCAN_TEST.state.completion.complete=false;true')
        routes_ok=all(x['visible']==1 and x['sw']<=x['vw']+1 for x in per_routes.values())
        worked_ok=worked['left']>=-1 and worked['right']<=worked['vw']+1 and worked['sw']<=worked['vw']+1 and worked['steps']==5
        practice_ok=practice_m['filledLeft']>=-1 and practice_m['filledRight']<=practice_m['vw']+1 and practice_m['formLeft']>=-1 and practice_m['formRight']<=practice_m['vw']+1 and practice_m['sw']<=practice_m['vw']+1 and practice_m['fields']==5
        city_ok=city['hLeft']>=-1 and city['hRight']<=city['vw']+1 and city['kLeft']>=-1 and city['kRight']<=city['vw']+1 and city['sw']<=city['vw']+1 and city['helsinkiParts']==5 and city['helsinkiCta']=='Переглянути Helsinki Region Infoshare →' and '🇺🇦 Український приклад · Київ' in city['kyivTitle'] and 'data.kyivcity.gov.ua' in city['kyivLink'] and city['wuaRole'] and city['wuaMastery']
        completion_ok=completion['left']>=-1 and completion['right']<=completion['vw']+1 and completion['sw']<=completion['vw']+1 and completion['transfer'] and completion['wua'] and completion['responsibility']
        viewport_results[str(w)]={'pass':routes_ok and pop_ok and worked_ok and practice_ok and city_ok and completion_ok,'routes':per_routes,'popover':pop,'workedExample':worked,'practicePortfolio':practice_m,'cityPractice':city,'completion':completion}
        ck(f'bounded responsive smoke {w}px',viewport_results[str(w)]['pass'],json.dumps(viewport_results[str(w)],ensure_ascii=False))
        # screenshot corrected practice/Portfolio route for evidence
        show_route('wua');time.sleep(.03)
        eval_js('document.querySelector(".kyiv-case").scrollIntoView({block:"center",behavior:"instant"});true');time.sleep(.04)
        shot=call('Page.captureScreenshot',{'format':'png','fromSurface':True})['result']['data']
        (ROOT/f'qa/final-learner-facing-{w}.png').write_bytes(base64.b64decode(shot))

    # Term closure behavior representative bounded smoke.
    set_view(1440,900);show_route('wua');time.sleep(.03)
    term_behavior=eval_js('''(async()=>{const a=document.querySelector('.term-trigger[data-term="analytical-resource"]');const b=document.querySelector('.term-trigger[data-term="relevant-data"]');a.click();await new Promise(r=>requestAnimationFrame(r));const first=a.getAttribute('aria-expanded');b.click();await new Promise(r=>requestAnimationFrame(r));const single=[...document.querySelectorAll('.term-trigger[aria-expanded="true"]')].length;b.focus();b.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));await new Promise(r=>requestAnimationFrame(r));const escapeClosed=document.getElementById('term-note-popover').hidden;a.click();await new Promise(r=>requestAnimationFrame(r));document.body.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}));await new Promise(r=>requestAnimationFrame(r));return {first,single,escapeClosed,outsideClosed:document.getElementById('term-note-popover').hidden};})()''')
    ck('representative Term Note single-open/Escape/outside behavior',term_behavior['first']=='true' and term_behavior['single']==1 and term_behavior['escapeClosed'] and term_behavior['outsideClosed'],json.dumps(term_behavior))

    errors=eval_js('window.__qaErrors.slice()')
    console_errors=[]
    for e in events:
        if e.get('method')=='Runtime.exceptionThrown':console_errors.append(e)
        if e.get('method')=='Log.entryAdded' and e.get('params',{}).get('entry',{}).get('level')=='error':console_errors.append(e)
    ck('browser runtime exceptions zero',not errors and not console_errors,f'window={errors}; events={len(console_errors)}')
    status='PASS' if all(c['pass'] for c in checks) else 'ISSUE'
    report={'candidate':'UCAN_Lesson_10_HTML_Preview_v1.7_FinalCandidate_PreQA','browser':ver.get('product'),'userAgent':ver.get('userAgent'),'runtimeMethod':'Chromium DevTools Page.setDocumentContent on about:blank with exact candidate HTML/CSS/JS inlined; localStorage shim only for bounded Pre-QA smoke because managed Chromium blocks local URL navigation','viewports':viewport_results,'status':status,'checks':checks,'counts':{'checks':len(checks),'failed':sum(not c['pass'] for c in checks)},'scope':'Bounded final learner-facing refinement smoke only; not full Independent HTML/LMS QA'}
    (ROOT/'qa/final-learner-facing-browser-smoke-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for c in checks:print(('PASS' if c['pass'] else 'FAIL'),c['name'],c['detail'])
    print('BROWSER',ver.get('product'));print('STATUS',status,'FAILED',report['counts']['failed'])
    sys.exit(0 if status=='PASS' else 1)
finally:
    if ws:
        try:ws.close()
        except:pass
    proc.terminate()
    try:proc.wait(3)
    except:proc.kill()
