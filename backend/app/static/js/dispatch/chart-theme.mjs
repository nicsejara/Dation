/** Presentation-only ECharts options. Data, units and callbacks stay with callers. */
export function chartPalette(root){
  const style=getComputedStyle(root);
  const role=(name,fallback)=>style.getPropertyValue(name).trim()||fallback;
  return {
    text:role('--color-text','#f3f8fa'),secondary:role('--color-text-secondary','#b8c8cf'),
    muted:role('--color-text-muted','#91a5af'),surface:role('--color-surface-overlay','#172731'),
    border:role('--color-border-strong','#67838f'),grid:role('--color-border','rgba(145,189,199,.18)'),
    onSeries:role('--d-bg-0','#071015'),
    series:['#50cec7','#79b9f0','#c1a4ef','#f0bc67','#b1d897','#ed9bb2'],
  };
}
const mapOption=(value,transform)=>Array.isArray(value)?value.map(transform):transform(value||{});
export function themedChartOptions(options,palette,width=Infinity){
  const axis=value=>({...value,
    nameTextStyle:{...value.nameTextStyle,color:palette.secondary},
    axisLabel:{hideOverlap:true,...value.axisLabel,color:palette.secondary},
    axisLine:{...value.axisLine,lineStyle:{...value.axisLine?.lineStyle,color:palette.border}},
    axisTick:{...value.axisTick,lineStyle:{...value.axisTick?.lineStyle,color:palette.border}},
    splitLine:{...value.splitLine,lineStyle:{...value.splitLine?.lineStyle,color:palette.grid}},
    splitArea:{...value.splitArea,areaStyle:{...value.splitArea?.areaStyle,color:['transparent','transparent']}},
  });
  const label=value=>({...value,color:String(value?.position||'').startsWith('inside')?palette.onSeries:palette.text});
  const output={...options,color:palette.series,backgroundColor:'transparent',
    textStyle:{fontFamily:'inherit',fontSize:12,...options.textStyle,color:palette.text},
    aria:{...options.aria,enabled:true},
    tooltip:mapOption(options.tooltip,value=>({...value,
      backgroundColor:palette.surface,borderColor:palette.border,
      textStyle:{...value.textStyle,color:palette.text},
      axisPointer:{...value.axisPointer,
        lineStyle:{...value.axisPointer?.lineStyle,color:palette.muted},
        label:{...value.axisPointer?.label,backgroundColor:palette.surface,color:palette.text},
      },
    })),
  };
  for(const key of ['xAxis','yAxis','radiusAxis','angleAxis'])if(options[key])output[key]=mapOption(options[key],axis);
  if(options.legend)output.legend=mapOption(options.legend,value=>({...value,
    textStyle:{...value.textStyle,color:palette.secondary},
    pageTextStyle:{...value.pageTextStyle,color:palette.secondary},
    pageIconColor:palette.text,pageIconInactiveColor:palette.muted,
  }));
  if(options.title)output.title=mapOption(options.title,value=>({...value,textStyle:{...value.textStyle,color:palette.text},subtextStyle:{...value.subtextStyle,color:palette.secondary}}));
  if(options.series)output.series=options.series.map(value=>({...value,
    ...(value.label?{label:label(value.label)}:{}),
    ...(value.emphasis?{emphasis:{...value.emphasis,...(value.emphasis.label?{label:label(value.emphasis.label)}:{})}}:{}),
  }));
  if(width<480&&options.grid&&!Array.isArray(options.grid)&&Number(options.grid.left)>100){
    output.grid={...options.grid,left:96,right:16};
    if(output.yAxis)output.yAxis=mapOption(output.yAxis,value=>({...value,axisLabel:{...value.axisLabel,width:84,overflow:'truncate'}}));
  }
  return output;
}
