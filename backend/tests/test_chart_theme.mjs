import test from 'node:test';
import assert from 'node:assert/strict';
import {themedChartOptions} from '../app/static/js/dispatch/chart-theme.mjs';
const palette={text:'#f3f8fa',secondary:'#b8c8cf',muted:'#91a5af',surface:'#172731',border:'#67838f',grid:'#304550',onSeries:'#071015',series:['#50cec7','#79b9f0']};

test('chart theme preserves data, callbacks, font and caller options without mutation',()=>{
  const formatter=value=>'día '+value,values=[{value:4,itemStyle:{opacity:0}},7];
  const input={textStyle:{fontSize:16,fontFamily:'Example',fontWeight:700},grid:{left:170},
    tooltip:{trigger:'item',renderMode:'richText',formatter,valueFormatter:formatter},
    xAxis:{type:'value',axisLabel:{formatter}},yAxis:{type:'category',data:['A','B']},
    series:[{type:'bar',data:values,label:{show:true,position:'inside',formatter}}],aria:{description:'Datos operativos'}};
  const before=structuredClone({...input,tooltip:{},xAxis:{type:'value'},series:[]});
  const output=themedChartOptions(input,palette,1440);
  assert.equal(output.series[0].data,values);assert.equal(output.series[0].label.formatter,formatter);
  assert.equal(output.tooltip.formatter,formatter);assert.equal(output.tooltip.valueFormatter,formatter);
  assert.equal(output.xAxis.axisLabel.formatter,formatter);assert.equal(output.tooltip.renderMode,'richText');
  assert.equal(output.textStyle.fontSize,16);assert.equal(output.textStyle.fontFamily,'Example');assert.equal(output.textStyle.fontWeight,700);
  assert.equal(output.series[0].label.color,palette.onSeries);assert.equal(output.tooltip.backgroundColor,palette.surface);
  assert.equal(output.aria.description,'Datos operativos');assert.equal(output.aria.enabled,true);
  assert.deepEqual({...input,tooltip:{},xAxis:{type:'value'},series:[]},before);
  assert.equal(input.series[0].label.color,undefined);assert.equal(input.tooltip.backgroundColor,undefined);
});

test('multiple axes, legends and titles retain formatters and use dark label roles',()=>{
  const format=value=>'$ '+value;
  const output=themedChartOptions({xAxis:[{type:'value',axisLabel:{formatter:format}},{type:'category',data:['A']}],
    legend:[{type:'scroll',textStyle:{fontSize:14}}],title:{text:'Capacidad'},
    series:[{type:'line',lineStyle:{type:'dashed'},data:[3],label:{position:'top'}}]},palette);
  assert.equal(output.xAxis.length,2);assert.equal(output.xAxis[0].axisLabel.formatter,format);
  assert.equal(output.xAxis[1].axisLabel.color,palette.secondary);
  assert.equal(output.legend[0].type,'scroll');assert.equal(output.legend[0].textStyle.fontSize,14);
  assert.equal(output.title.text,'Capacidad');assert.equal(output.title.textStyle.color,palette.text);
  assert.equal(output.series[0].lineStyle.type,'dashed');assert.equal(output.series[0].label.color,palette.text);
});

test('compact chart layout changes label space while preserving schedule offsets and durations',()=>{
  const data=[2,4,7],input={grid:{left:170,right:28,bottom:45},yAxis:{type:'category',data:['V1','V2']},
    series:[{type:'bar',silent:true,itemStyle:{opacity:0},data},{type:'bar',data:[1,2,3]}]};
  const output=themedChartOptions(input,palette,320);
  assert.equal(output.grid.left,96);assert.equal(output.grid.bottom,45);
  assert.equal(output.yAxis.axisLabel.width,84);assert.equal(output.series[0].itemStyle.opacity,0);
  assert.equal(output.series[0].data,data);assert.deepEqual(output.series[1].data,[1,2,3]);
  assert.equal(input.grid.left,170);assert.equal(input.yAxis.axisLabel,undefined);
});
