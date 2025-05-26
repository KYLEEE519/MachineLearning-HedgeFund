/* eslint-disable @typescript-eslint/no-explicit-any */
"use client"
import { useState } from 'react';
import Filter from '@/components/filter';
// import Chart from '@/components/chart';
import ChartGroup from '@/components/chart/group';
import Table from '@/components/table';
import type { Data } from '@/app/api/backtester/data'
import { Input } from 'antd';

export default function Home() {
  const [data, setData] = useState<Data>();

  const onFinish = async () => {
    return fetch('/api/backtester').then(async (res) => {
      if (res.ok) {
        const { data } = await res.json()
        setData(data)
        console.info('data: ', data)
        return
      }
      throw new Error('Network response was not ok');
    })
  }


  return (
    <div className="w-full flex justify-center flex-col">
      <Filter onFinish={onFinish} />
      {data && (
        <>
          <Input.TextArea
            autoSize
            className='mb-2! border-gray-400! border-dashed! rounded-md!'
            value={data[0].toString().replace(/^\n/g, '').replace(/\n$/g, '')}
          />
          {/* <Chart id='backtester' data={data} />
          <Chart id='balanceChange' data={data} />
          <Chart id='tradingProfit' data={data} />
          <Chart id='revenueCurve' data={data} />
          <Chart id='reboundCurve' data={data} />
          <Chart id='incomeComparison' data={data} />
          <Chart id='durationVsIncome' data={data} /> */}
          <ChartGroup data={data} ids={['backtester', 'balanceChange', 'tradingProfit', 'revenueCurve', 'reboundCurve', 'incomeComparison', 'durationVsIncome']} />
          <Table data={data} />
        </>
      )}
    </div>
  );
}
