import * as echarts from 'echarts';
import { useEffect, useRef, useState } from 'react';
import Handlers from './handler'
import type { Data } from '@/app/api/backtester/data'


interface Props {
    id: keyof typeof Handlers
    data: Data
}

export default function Chart({ id, data: _data }: Props) {
    const ref = useRef(null);
    const [title, setTitle] = useState('')

    useEffect(() => {
        const { handler, title } = Handlers[id]
        setTitle(title)
        const option = handler(_data)
        const myChart = echarts.init(ref.current);
        myChart.setOption(option);
    }, [])

    return (
        <div className='border-[1px] border-gray-400 border-dashed rounded-md mb-2'>
            <div className='w-fit p-1 m-2 border-[1px] border-gray-600 border-dashed rounded-md'>{ title }</div>
            <div ref={ref} className='w-[100%] h-[460px]' />
        </div>
    )
}