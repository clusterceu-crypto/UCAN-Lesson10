from pathlib import Path
from bs4 import BeautifulSoup
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
PRED=Path('/mnt/data/l10_v17_work/UCAN_Lesson_10_HTML_Preview_v1.6_PreQA')
html=(ROOT/'index.html').read_text(encoding='utf-8')
pred_html=(PRED/'index.html').read_text(encoding='utf-8')
config=(ROOT/'js/lesson10.config.js').read_text(encoding='utf-8')
pred_config=(PRED/'js/lesson10.config.js').read_text(encoding='utf-8')
soup=BeautifulSoup(html,'html.parser'); psoup=BeautifulSoup(pred_html,'html.parser')
checks=[]
def ck(name,ok,detail=''): checks.append({'name':name,'pass':bool(ok),'detail':str(detail)})

# Identity / routes
ck('artifact config version 1.7',"packageVersion: '1.7'" in config)
routes=[x.get('data-route') for x in soup.select('.lesson-page')]
ck('route inventory remains 10',routes==['start','open-data','principles','decision','wua','resources','portfolio','practice','assessment','completion'],routes)
ck('route labels retained',all(x in config for x in ["{id:'portfolio',label:'Навчальний приклад'}","{id:'practice',label:'Практика і міні-карта'}"]))

# Final learner sequence
idx={r:i for i,r in enumerate(routes)}
ck('resources before worked example/practice',idx['wua']<idx['resources']<idx['portfolio']<idx['practice']<idx['assessment'],idx)
wua=soup.select_one('[data-route="wua"]')
children=[x for x in wua.children if getattr(x,'name',None)]
def pos(selector):
    el=wua.select_one(selector)
    return children.index(el) if el in children else -1
ck('WUA -> Helsinki -> Kyiv sequence in city/example route',pos('.helsinki-case')>0 and pos('.kyiv-case')>pos('.helsinki-case'),{'helsinki':pos('.helsinki-case'),'kyiv':pos('.kyiv-case')})
ck('supporting resources after Kyiv',idx['resources']==5)
portfolio=soup.select_one('[data-route="portfolio"]'); practice=soup.select_one('[data-route="practice"]')
ck('worked example five steps',len(portfolio.select('.decision-stepper>li'))==5)
ck('same-example cue in all five steps',sum('У тому самому прикладі:' in x.get_text(' ',strip=True) for x in portfolio.select('.decision-stepper .example-line'))==5)
practice_children=[x for x in practice.children if getattr(x,'name',None)]
pp={}
for i,x in enumerate(practice_children):
    if x.get('id') in ['formative-form','portfolio-form']: pp[x.get('id')]=i
    if 'filled-card' in (x.get('class') or []): pp['filled-card']=i
ck('formative before completed mini-card before learner form',pp.get('formative-form',999)<pp.get('filled-card',999)<pp.get('portfolio-form',999),pp)
ck('Portfolio three-stage rhythm',all(t in practice.get_text(' ',strip=True) for t in ['1. Подивіться на завершений приклад','2. Створіть свою карту','3. Перевірте перед збереженням']))

# Plain language pass
visible=soup.get_text(' ',strip=True)
for token in ['WUA-артефакт','концептуальне розрізнення','керовані запитання']:
    ck(f'plain-language prohibited phrase removed: {token}',token not in visible)
# plain 'артефакт' must not be learner-visible
ck('learner-facing артефакт removed',not re.search(r'(?i)\bартефакт\w*\b',visible),re.findall(r'(?i)\bартефакт\w*\b',visible))
ck('relevant data first-use explained in plain language','дані, які справді стосуються її питання' in wua.get_text(' ',strip=True))
resources=soup.select_one('[data-route="resources"]')
ck('resource framing says mastery not required','не потрібно освоювати жодну зовнішню платформу' in resources.get_text(' ',strip=True))

# WUA learner integration
wtext=wua.get_text(' ',strip=True)
ck('WUA role explanation present','Роль WUA в цьому занятті.' in wtext and 'лише як приклад спеціалізованого аналітичного ресурсу' in wtext)
ck('WUA platform mastery not required','не потрібно вміти працювати з платформою WUA' in wtext)
ck('WUA separate task burden removed','окремо описувати його у Вашому завданні не потрібно' in wtext)
ck('old external-resource warning removed','Якщо зовнішній ресурс тимчасово недоступний' not in wtext)
wua_link=wua.select_one('a[href="https://wua.digital/uk/"]')
ck('WUA remains optional text link',wua_link is not None and 'За бажанням' in wtext and not wua.select('img,svg'))
ck('WUA boundary retained','Джерело даних ≠ публікація відкритих даних ≠ аналітичний ресурс ≠' in wtext)

# Helsinki protected case + action CTA
hels=wua.select_one('.helsinki-case'); phels=psoup.select_one('.helsinki-case')
ck('Helsinki controlled five case-parts unchanged',[x.get_text(' ',strip=True) for x in hels.select('.case-part')]==[x.get_text(' ',strip=True) for x in phels.select('.case-part')])
ck('Helsinki action invitation present','Ознайомтеся, як Helsinki організував доступ' in hels.get_text(' ',strip=True))
hri=hels.select_one('a[href="https://hri.fi/en_gb/"]')
ck('Helsinki CTA clear',hri is not None and hri.get_text(' ',strip=True)=='Переглянути Helsinki Region Infoshare →')

# Kyiv official case
kyiv=wua.select_one('.kyiv-case')
kyiv_text=kyiv.get_text(' ',strip=True) if kyiv else ''
ck('Kyiv case inserted',kyiv is not None and '🇺🇦 Український приклад · Київ' in kyiv_text)
ck('Kyiv official portal claim bounded','офіційний міський Портал даних' in kyiv_text and 'єдину точку доступу до публічної інформації у форматі відкритих даних' in kyiv_text)
ck('Kyiv datasets/dashboard analytical tools claim bounded','набори даних' in kyiv_text and 'інтерактивні дашборди' in kyiv_text and 'інструменти аналітики' in kyiv_text)
ck('Kyiv municipal publishers claim bounded',all(x in kyiv_text for x in ['структурні підрозділи КМДА','районні адміністрації','комунальні підприємства']))
kyiv_link=kyiv.select_one('a[href="https://data.kyivcity.gov.ua/"]') if kyiv else None
ck('Kyiv link official portal only',kyiv_link is not None and kyiv_link.get_text(' ',strip=True)=='Переглянути Портал даних Києва →')
for bad in ['автоматично покращ','інвестиційн','гарантує якість','гарантує повноту']:
    ck(f'Kyiv unsupported claim absent: {bad}',bad not in kyiv_text.lower())
ck('Helsinki/Kyiv relationship clear','Helsinki дає міжнародний орієнтир, а Київ — український муніципальний приклад' in wtext)

# Protected architecture against v1.6
pred_form=psoup.select_one('#formative-form'); new_form=soup.select_one('#formative-form')
ck('formative form content unchanged',str(pred_form)==str(new_form))
pred_assess=psoup.select_one('#assessment-form'); new_assess=soup.select_one('#assessment-form')
ck('final assessment HTML unchanged',str(pred_assess)==str(new_assess))
# Portfolio form shell unchanged
ck('portfolio form HTML unchanged',str(psoup.select_one('#portfolio-form'))==str(soup.select_one('#portfolio-form')))
# Config core protected blocks unchanged
for block, start, end in [
    ('terms','terms: {','  portfolio:{artifactTitle:'),
    ('portfolio','portfolio:{artifactTitle:','  formative:'),
    ('formative','formative:{','  assessment:'),
    ('assessment','assessment:{','  resources:['),
]:
    a=pred_config.split(start,1)[1].split(end,1)[0]
    b=config.split(start,1)[1].split(end,1)[0]
    ck(f'config protected block unchanged: {block}',a==b)
ck('shared runtime unchanged',(ROOT/'js/shared.js').read_bytes()==(PRED/'js/shared.js').read_bytes())
ck('lesson runtime unchanged',(ROOT/'js/lesson10.js').read_bytes()==(PRED/'js/lesson10.js').read_bytes())
ck('CSS runtime shell unchanged',(ROOT/'css/shared.css').read_bytes()==(PRED/'css/shared.css').read_bytes())
portfolio_block=config.split("portfolio:{artifactTitle:",1)[1].split("]},\n  formative:",1)[0]
ck('exact five portfolio config fields',sum(portfolio_block.count(f"{{id:'{k}'") for k in ['decision','data','conditions','principle','value'])==5 and all(portfolio_block.count(f"{{id:'{k}'")==1 for k in ['decision','data','conditions','principle','value']))
ck('formative correct C protected',"formative:{correct:'C'" in config)
ck('assessment keys B/C/A/D/B protected',"answers:{q1:'B',q2:'C',q3:'A',q4:'D',q5:'B'}" in config and "passScore:5,total:5" in config)
ck('generic resource count remains four',config.count("{name:")==4)
ck('Kyiv not added to generic resource config','data.kyivcity.gov.ua' not in config)

# Term Note system
terms=soup.select('.term-inline[data-term]'); term_keys=[t.get('data-term') for t in terms]
ck('14 body term placeholders',len(terms)==14 and len(set(term_keys))==14,(len(terms),term_keys))
ck('zero term placeholders in headings/subtitle',len(soup.select('h1 .term-inline,h2 .term-inline,h3 .term-inline,h4 .term-inline,h5 .term-inline,h6 .term-inline,.lesson-subtitle .term-inline'))==0)
ck('no detached/expanding definition blocks',not soup.select('.term-host,.term-definition'))
ck('term popover runtime retained','term-note-popover' in (ROOT/'js/lesson10.js').read_text(encoding='utf-8') and 'max-width:680px' in (ROOT/'css/shared.css').read_text(encoding='utf-8'))

# Completion transfer
completion=soup.select_one('[data-route="completion"]'); ctext=completion.get_text(' ',strip=True)
ck('completion concrete team transfer action','візьміть завершену міні-карту на робочу розмову' in ctext and 'що потребує оновлення' in ctext and 'до остаточного рішення' in ctext)
ck('completion analytical-support connection','аналітичні ресурси на кшталт WUA' in ctext and 'впорядковувати, перевіряти, аналізувати' in ctext)
ck('completion municipal responsibility retained','залишаються відповідальністю міської команди' in ctext)

# Metadata/features exclusions
for token in ['[TERM:','L10-H','Drive ID','synthesis-register','QA Gate','PreQA','v1.3','v1.4','v1.5','v1.6','v1.7']:
    ck(f'learner metadata excluded: {token}',token not in visible)
ck('AI controls absent','ChatGPT' not in visible and 'Gemini' not in visible and 'ai-support' not in html.lower() and 'ai-prompt' not in html.lower())
ck('video absent',not soup.select('video,iframe') and 'Відео-блок' not in visible)
ck('no generated learner images',not soup.select('img,svg'))

status='PASS' if all(c['pass'] for c in checks) else 'ISSUE'
report={'candidate':'UCAN_Lesson_10_HTML_Preview_v1.7_FinalCandidate_PreQA','date':'2026-08-24','scope':'Bounded final learner-facing refinement static verification; not Independent QA','status':status,'checks':checks,'counts':{'checks':len(checks),'failed':sum(not c['pass'] for c in checks)}}
(ROOT/'qa/final-learner-facing-static-smoke-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for c in checks: print(('PASS' if c['pass'] else 'FAIL'),c['name'],c['detail'])
print('STATUS',status,'FAILED',report['counts']['failed'])
sys.exit(0 if status=='PASS' else 1)
