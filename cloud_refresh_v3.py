"""Verified public sources; unusable optional HTML never replaces valid ICS.

Required ICS validation and valid official-source disagreement remain fatal.
Only an HTML response lacking identifiable schedule structure is classified as
unusable optional evidence. Its URL, retrieval time and hash remain fault facts.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import public_calendar as c
import relay_core as r
from cloud_refresh import OfficialBrowser

def checked_optional(url,data):
    match=re.fullmatch(r'https://www\.bls\.gov/schedule/(\d{4})/(\d{2})_sched_list.htm',url)
    if not match:return data
    year,month=map(int,match.groups())
    doc=c.Document(data).root
    headings=[n.text() for tag in ('h1','h2','title') for n in doc.all(tag)]
    expected=f'{c.calendar.month_name[month]} {year}'
    tables=[t for t in doc.all('table') if any([n.text().lower() for n in c.cells(row)][:3]==['date','time','release'] for row in t.all('tr'))]
    if not any(expected in h for h in headings) or len(tables)!=1:
        at=getattr(data,'metadata',{}).get('retrieved_at') or datetime.now(c.ET).isoformat()
        raise c.SourceUnavailable('OPTIONAL_BLS_HTML_NOT_CALENDAR_OR_AMBIGUOUS; retrieved_at='+at+'; sha256='+c.sha(data)+'; bytes='+str(len(data)))
    # Once it IS an identifiable schedule, malformed dates/times and any later
    # valid ICS/HTML disagreement must fail the entire refresh.
    c.parse_bls(data,url,year,month)
    return data

def refresh(output,browser_factory=OfficialBrowser,get=c.fetch,observed=None,publish=r.publish):
    with browser_factory() as browser:
        def retrieve(url):
            try:data=get(url)
            except c.SourceUnavailable:
                if url.startswith('https://www.bls.gov/'):data=browser.fetch(url)
                else:raise
            result=checked_optional(url,data)
            print(json.dumps(dict(kind='PUBLIC_SOURCE_CAPTURE',url=url,sha256=c.sha(result),bytes=len(result),
                retrieved_at=getattr(result,'metadata',{}).get('retrieved_at') or datetime.now(c.ET).isoformat())),flush=True)
            return result
        body=r.create_bundle(observed,get=retrieve)
    return publish(output,body)

def self_test():
    import unittest,tempfile
    from unittest.mock import patch
    sys.path.insert(0,str(Path(__file__).resolve().parent/'tests'))
    from test_relay import NOW,captures
    url=c.bls_secondary_urls(NOW.date(),NOW.date()+c.timedelta(days=13))['bls_html_2026_11']
    shell=b'<html><title>November 2026</title><p>Noncalendar response shell</p></html>'
    valid=b'<html><title>November 2026</title><table><tr><th>Date</th><th>Time</th><th>Release</th></tr><tr><td>November 17, 2026</td><td>08:30 AM</td><td>Employment Situation</td></tr></table></html>'
    class Optional(unittest.TestCase):
        def build(self,primary=True,secondary=shell,broken=False):
            data=captures();data[url]=secondary
            if not primary:data.pop(c.BLS_ICS)
            if broken:data[c.BLS_ICS]=b'<html>Not ICS</html>'
            class Browser:
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def fetch(self,u):
                    if u not in data:raise c.SourceUnavailable('Unavailable fixture source')
                    return data[u]
            def get(u):
                if u.startswith('https://www.bls.gov/'):raise c.SourceUnavailable('403 fixture')
                return data[u]
            return refresh(Path('unused'),Browser,get,NOW,lambda output,body:r.verify_bundle(body,c.sha(body),NOW))
        def test_optional_shell_is_rejected_without_masking_required_ics(self):
            b=self.build();self.assertIn('bls_ics',b['source_manifest']);self.assertNotIn('bls_html_2026_11',b['source_manifest'])
            self.assertIn('OPTIONAL_BLS_HTML_NOT_CALENDAR_OR_AMBIGUOUS',b['retrieval_failures']['bls_html_2026_11']['error'])
        def test_ambiguous_optional_tables_are_unusable_not_verified(self):
            b=self.build(secondary=valid+valid);self.assertNotIn('bls_html_2026_11',b['source_manifest'])
            self.assertIn('AMBIGUOUS',b['retrieval_failures']['bls_html_2026_11']['error'])
        def test_ambiguous_secondary_cannot_supply_missing_bls(self):
            with self.assertRaises(c.InvalidCalendar):self.build(primary=False,secondary=valid+valid)
        def test_missing_ics_and_unusable_secondary_still_fail_closed(self):
            with self.assertRaises(c.InvalidCalendar):self.build(primary=False)
        def test_malformed_ics_is_never_masked_by_optional_source_status(self):
            with self.assertRaises(c.InvalidCalendar):self.build(broken=True)
        def test_valid_authoritative_disagreement_still_blocks_publication(self):
            with self.assertRaises(c.InvalidCalendar):self.build(secondary=valid)
    import socket
    with patch.object(socket,'socket',side_effect=AssertionError('OFFLINE SELF TEST')):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Optional))
    return result.wasSuccessful()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true');p.add_argument('--output',type=Path,default=Path('public'))
    args=p.parse_args()
    if args.self_test:raise SystemExit(not self_test())
    print(refresh(args.output))
