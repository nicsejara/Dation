// Build instructions and pinned dependencies: docs/architecture.md.
import {use, init, getInstanceByDom} from 'echarts/core';
import {BarChart, LineChart, ScatterChart} from 'echarts/charts';
import {GridComponent, TooltipComponent, LegendComponent, AriaComponent} from 'echarts/components';
import {SVGRenderer} from 'echarts/renderers';
use([BarChart, LineChart, ScatterChart, GridComponent, TooltipComponent, LegendComponent, AriaComponent, SVGRenderer]);
export {init, getInstanceByDom};
