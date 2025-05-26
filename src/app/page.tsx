"use client";
import { Badge, List } from 'antd';
import {
  FireOutlined
} from '@ant-design/icons';

const data = [
  '/backtesterA',
  '/backtesterB',
].map((item, index) => ({ label: `模块 ${index + 1}`, url: item }));

export default function Home() {
  return (
    <div className="mt-2">
      <Badge count={data.length}>
        <List
          bordered
          dataSource={data}
          renderItem={(row) => (
            <List.Item>
              <a href={row.url} target=''>
                <FireOutlined />&nbsp;{row.label}
              </a>
            </List.Item>
          )}
        />
      </Badge>
    </div>
  );
}
