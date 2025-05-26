import React from 'react';
import { Tabs } from 'antd';
import Chart from './index'
import Handlers from './handler'
import type { Data } from '@/app/api/backtester/data'

interface Props {
    ids: Array<keyof typeof Handlers>
    data: Data
}



const App = (props: Props) => {

    const getItems = () => {
        return props.ids.map((id) => ({
            key: id as string,
            label: id,
            children: <Chart id={id} data={props.data} />
        }))
    }

    return <Tabs defaultActiveKey={props.ids[0] as string} items={getItems()} />
};

export default App;

          