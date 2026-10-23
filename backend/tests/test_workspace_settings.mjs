import test from 'node:test';
import assert from 'node:assert/strict';
import {readSettingsTab,writeSettingsTab} from '../app/static/js/platform/settings-resource.mjs';
import {readResource,resourceUrl} from '../app/static/js/dispatch/navigation/resource.mjs';
import {workspaceDate,workspaceNumber} from '../app/static/js/platform/workspace-format.mjs';

test('settings tabs validate links and restore the selected resource',()=>{
 assert.equal(readSettingsTab('/app/settings'),'general');
 for(const tab of ['general','operation','ddas','plan']){const url=writeSettingsTab(new URL('https://example.test/app/settings'),tab);assert.equal(readSettingsTab(url),tab);}
 assert.throws(()=>readSettingsTab('/app/settings?settings_tab=payments'));assert.throws(()=>writeSettingsTab(new URL('https://example.test'),'<script>'));
});
test('the shared router clears workspace settings from DDA URLs',()=>{
 const url=resourceUrl('https://example.test/app/settings?settings_tab=plan&case_id=old&run_id=old',{view:'settings',settingsTab:'operation'});
 assert.equal(readResource(url).settingsTab,'operation');assert.equal(url.searchParams.has('case_id'),false);
 const next=resourceUrl(url,{view:'platform-home'});assert.equal(next.searchParams.has('settings_tab'),false);assert.equal(next.pathname,'/app');
});
test('workspace formats honor locale/timezone without converting stored quantities',()=>{
 const values={amount:1234.5,weight:1000};
 assert.equal(workspaceNumber(values.amount,{language:'en',country:'US'}),'1,234.5');assert.equal(workspaceNumber(values.amount,{language:'es',country:'AR'}),'1.234,5');
 assert.equal(workspaceDate('2026-01-15T02:30:00Z',{timezone:'America/Argentina/Buenos_Aires'},{day:'numeric'}),'14');
 assert.equal(workspaceDate('bad',{}),'Sin registro');assert.equal(workspaceDate('2026-01-15T02:30:00Z',{timezone:'invalid'},{day:'numeric'}),'15');
 assert.deepEqual(values,{amount:1234.5,weight:1000});
});

test('relative workspace dates retain readable human timing, including future and invalid events',async()=>{
 const {workspaceRelativeDate}=await import('../app/static/js/platform/workspace-format.mjs');
 const now=Date.parse('2026-10-20T12:00:00Z'),zone={language:'es',country:'AR',timezone:'America/Argentina/Buenos_Aires'};
 assert.equal(workspaceRelativeDate('2026-10-20T11:58:00Z',zone,now),'hace 2 minutos');
 assert.equal(workspaceRelativeDate('2026-10-20T14:00:00Z',zone,now),'dentro de 2 horas');
 assert.equal(workspaceRelativeDate('2026-10-19T12:00:00Z',zone,now),'ayer');
 assert.equal(workspaceRelativeDate('bad',zone,now),'Sin registro');assert.equal(workspaceRelativeDate(null,zone,now),'Sin registro');
});
