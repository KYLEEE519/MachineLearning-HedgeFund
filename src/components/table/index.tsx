import { Table } from 'antd';
import type { Data } from '@/app/api/backtester/data'


interface Props {
    data: Data
}

export default function _Table({ data }: Props) {
    const columns = data[12].headers?.map(key => ({ key, title: key, dataIndex: key }))
    const dataSource = data[12].data?.map((row, index) => {
        const d: { [key: string]: unknown } = { key: index }
        data[12].headers?.forEach((key, index) => {
            d[key] = row[index] === null ? 'null' : row[index]
        })
        return d
    })
    return <div className='border-[1px] border-gray-400 border-dashed rounded-md p-2 pb-0'>
        <Table columns={columns} dataSource={dataSource} />
    </div>
}