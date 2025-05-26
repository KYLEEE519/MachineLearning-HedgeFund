import type { Data } from '@/app/api/backtester/data'
import dayjs from 'dayjs';

function parseGradioBdata(bdata: string, dtype = "f8") {
    if (dtype !== "f8") {
      throw new Error(`不支持的数据类型: ${dtype}`);
    }
    // 1. base64 解码为二进制字符串
    const binaryStr = atob(bdata);
    // 2. 转为 Uint8Array（字节数组）
    const len = binaryStr.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryStr.charCodeAt(i);
    }
    // 3. 用 Float64Array 解析为 float64 数组
    const float64Array = new Float64Array(bytes.buffer);
    // 4. 转为普通数组返回
    return Array.from(float64Array);
}

const handlerBacktester = (_data: Data) => {
    const { data } = JSON.parse(_data[1].plot!)
    const x = [...data[0].x, ...data[1].x, ...data[2].x].map(d => dayjs(d)).sort((a, b) => a.valueOf() - b.valueOf()).map(d => d.format('YYYY-MM-DD HH:mm:ss'))

    const y1 = new Array(x.length).fill(0)
    const y1Index = x.findIndex(d => d === dayjs(data[1].x).format('YYYY-MM-DD HH:mm:ss'))
    y1[y1Index] = data[1].y

    const lines = [
        {
            x: data[0].x,
            y: parseGradioBdata(data[0].y.bdata)
        },
        {
            x: data[1].x,
            y: y1
        },
        {
            x: data[2].x,
            y: data[2].y
        }
    ]
    const option = {
        xAxis: {
          type: 'category',
        //   data: lines[0].x,
          data: lines[0].x.map((d: number) => dayjs(d).format('YYYY-MM-DD HH:mm:ss')),
        },
        yAxis: {
          type: 'value',
          min: Math.ceil(Math.min(...lines[0].y)),
          max: Math.ceil(Math.max(...lines[0].y)),
        },
        series: [
          {
            data: lines[0].y,
            type: 'line',
            lineStyle: {
              color: '#5470C6',
              width: 2,
            },
          },
        //   {
        //     data: lines[1].y,
        //     type: 'line',
        //     symbol: 'triangle',
        //     symbolSize: 20,
        //     lineStyle: {
        //       color: '#5470C6',
        //       width: 2,
        //       type: 'dashed'
        //     },
        //     itemStyle: {
        //       borderWidth: 2,
        //       borderColor: '#EE6666',
        //       color: 'yellow'
        //     }
        //   },
        //   {
        //     data: lines[2].y,
        //     type: 'line',
        //     symbol: 'triangle',
        //     symbolSize: 20,
        //     lineStyle: {
        //       color: 'red',
        //       width: 2,
        //       type: 'dashed'
        //     },
        //     itemStyle: {
        //       borderWidth: 2,
        //       borderColor: '#EE6666',
        //       color: 'yellow'
        //     }
        //   }
        ],
    };
    return option
}
const handlerBalanceChange = (_data: Data) => {
    const { data } = JSON.parse(_data[2].value?.plot as string)
    const option = {
        xAxis: {
          type: 'category',
          data: data[0].x.map((d: number) => dayjs(d).format('YYYY-MM-DD HH:mm:ss')),
        },
        yAxis: {
          type: 'value',
          min: Math.ceil(Math.min(...data[0].y)),
          max: Math.ceil(Math.max(...data[0].y)),
        },
        series: [
          {
            data: data[0].y,
            type: 'line',
            lineStyle: {
              color: '#5470C6',
              width: 2,
            },
          },
        ],
    };
    return option
}
const handlerTradingProfit = (_data: Data) => {
    const { data } = JSON.parse(_data[3].value?.plot as string)
    const y = parseGradioBdata(data[0].y.bdata)
    const option = {
        xAxis: {
          type: 'category',
          data: data[0].x.map((d: number) => dayjs(d).format('YYYY-MM-DD HH:mm:ss')),
        },
        yAxis: {
          type: 'value',
          min: Math.ceil(Math.min(...y)),
          max: Math.ceil(Math.max(...y)),
        },
        series: [
          {
            data: y,
            type: 'bar',
            lineStyle: {
              color: '#5470C6',
              width: 2,
            },
          },
        ],
    };
    return option
}
const handlerRevenueCurve = (_data: Data) => {
    const { data } = JSON.parse(_data[4].value?.plot as string)
    const y = parseGradioBdata(data[0].y.bdata)
    const option = {
        xAxis: {
          type: 'category',
          data: data[0].x.map((d: number) => dayjs(d).format('YYYY-MM-DD HH:mm:ss')),
        },
        yAxis: {
          type: 'value',
          min: Math.ceil(Math.min(...y)),
          max: Math.ceil(Math.max(...y)),
        },
        series: [
          {
            data: y,
            type: 'line',
            lineStyle: {
              color: '#5470C6',
              width: 2,
            },
          },
        ],
    };
    return option
}
const handlerReboundCurve = (_data: Data) => {
    const { data } = JSON.parse(_data[5].value?.plot as string)
    const y = parseGradioBdata(data[0].y.bdata)
    const option = {
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: data[0].x.map((d: number) => dayjs(d).format('YYYY-MM-DD HH:mm:ss')),
        },
        yAxis: {
          type: 'value',
          min: Math.ceil(Math.min(...y)),
          max: Math.ceil(Math.max(...y)),
        },
        series: [
          {
            data: y,
            type: 'line',
            lineStyle: {
              color: '#5470C6',
              width: 2,
            },
            areaStyle: {}
          },
        ],
    };
    return option
}
const handlerIncomeComparison = (_data: Data) => {
    const { data } = JSON.parse(_data[6].value?.plot as string)
    const y = parseGradioBdata(data[0].y.bdata)
    const option = {
        xAxis: {
          type: 'category',
          data: data[0].x,
        },
        yAxis: {
          type: 'value',
        },
        series: [
          {
            data: y,
            type: 'bar',
          },
        ],
    };
    return option
}
const handlerDurationVsIncome = (_data: Data) => {
    const { data } = JSON.parse(_data[7].value?.plot as string)
    const x = parseGradioBdata(data[0].x.bdata)
    const y = parseGradioBdata(data[0].y.bdata)

    const option = {
        xAxis: {
          type: 'category',
          data: x,
        },
        yAxis: {
          type: 'value',
        },
        series: [
          {
            data: y,
            type: 'bar',
          },
        ],
    };
    return option
}

const D = {
    backtester: {
        title: '价格+交易点',
        handler: handlerBacktester,
    },
    balanceChange: {
        title: '平仓后账户余额变化',
        handler: handlerBalanceChange,
    },
    revenueCurve: {
        title: '累计收益曲线',
        handler: handlerRevenueCurve
    },
    reboundCurve: {
        title: '回涨曲线',
        handler: handlerReboundCurve
    },
    tradingProfit: {
        title: '每笔交易益付',
        handler: handlerTradingProfit
    },
    incomeComparison: {
        title: '对空益付对比',
        handler: handlerIncomeComparison,
    },
    durationVsIncome: {
        title: '持仓时长 VS 收益',
        handler: handlerDurationVsIncome,
    }
}
export default D as unknown as { [id: string]: { title: string, handler: (data: Data) => echarts.EChartsCoreOption } }
        