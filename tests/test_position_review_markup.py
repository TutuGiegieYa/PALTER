"""Execute the shared JS renderer without browser automation or production data."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import unittest

from tests import test_position_review as fixture


class Elements(HTMLParser):
    def __init__(self):
        super().__init__();self.tags=[];self.ids=[];self.text=[]
    def handle_starttag(self,tag,attrs):
        self.tags.append(tag);self.ids.extend(v for k,v in attrs if k=='id')
    def handle_data(self,data):self.text.append(data)


def render(results):
    source=Path('palter/static/ensemble.js').read_text()
    source=source[source.index('function concealmentReviewMarkup'):]
    helpers="const escapeHTML=s=>String(s??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));"
    script=helpers+'\n'+source+"\nconst input=JSON.parse(require('fs').readFileSync(0,'utf8'));process.stdout.write(conclusionReviewMarkup(input,a=>input.participants[a]?.name||a));"
    return subprocess.run(['node','-e',script],input=json.dumps(results),capture_output=True,text=True,check=True).stdout


class PositionMarkupTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.PositionReviewTests();self.f.setUp();self.addCleanup(self.f.doCleanups)

    def panel(self,html,actor):
        return html.split('id="ending-review-'+actor+'"',1)[1].split('<details class="ending-role-review"',1)[0]

    def test_investigator_and_culprit_have_distinct_sections_with_stable_ids(self):
        self.f.establish();self.f.defense();self.f.conclude();html=render(self.f.s['results'])
        panel=self.panel(html,self.f.killer)
        self.assertIn('立场与结案证据',panel);self.assertIn('形成完整定案的提交',panel)
        for old in ('最终论证判定','提交内容的证据核对','人物与机会','未亲自到访','证据链的缺口'):
            self.assertNotIn(old,panel)
        self.assertIn('最终论证判定',self.panel(html,self.f.investigator))
        parsed=Elements();parsed.feed(html);self.assertEqual(len(parsed.ids),len(set(parsed.ids)))
        self.assertIn('其他提交使用的材料（结案后对照）',panel)

    def test_admission_shows_confession_checks_only_for_actual_self_submission(self):
        self.f.f.acquire(fixture.IDS,self.f.killer);self.f.f.submit(fixture.IDS,self.f.killer)
        self.f.conclude();panel=self.panel(render(self.f.s['results']),self.f.killer)
        self.assertIn('供述与证据核对',panel);self.assertIn('责任与实施关联',panel)
        self.assertIn('本人供述',panel);self.assertNotIn('最终论证判定',panel)
        self.assertNotIn('提交内容的证据核对',panel)

    def test_historical_results_use_saved_objectives_without_fabricated_position_review(self):
        self.f.establish();self.f.defense(self.f.investigator);self.f.conclude(version='ai-tasks-v94.json')
        results=self.f.s['results'];before=deepcopy(results);html=render(results)
        panel=self.panel(html,self.f.killer)
        self.assertIn('旧版结案未记录独立的立场点评',panel);self.assertNotIn('证据链的缺口',panel)
        self.assertEqual(results,before)
        for p in results['participants'].values():
            p['reasoning']={k:v for k,v in p['reasoning'].items() if k in ('result','suspect','established')}
        panel=self.panel(render(results),self.f.killer)
        self.assertIn('对外立场与目标',panel);self.assertNotIn('指认与真相不符',panel)

    def test_model_and_submission_strings_are_escaped_not_executable(self):
        self.f.defense();self.f.conclude();results=self.f.s['results'];r=results['participants'][self.f.killer]['reasoning']
        hostile='<img src=x onerror="window.bad=true">'
        r['position_assessment']={'position_summary':hostile,'evidence_checks':[{'statement':hostile,
            'status':'unresolved','reason':hostile,'source_ids':[]}]}
        r['submission']['explanation']=hostile
        html=render(results);parser=Elements();parser.feed(html)
        self.assertNotIn('img',parser.tags);self.assertIn(hostile,parser.text)


if __name__=='__main__':unittest.main()
