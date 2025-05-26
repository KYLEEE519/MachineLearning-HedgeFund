"use client"
import React from 'react'
import { useState } from 'react';
import { Form, Select, Slider, Input, Row, Col, Button } from "antd"
import './style.css'

const Strategy = ['ma20', 'dualma', 'ThreeBarTrendStrategy', 'DualMaStrategy_model'].map((value) => ({ value, label: value }))
const Period = ['1m', '5m', '15m', '30m', '1h', '4h', '1d'].map((value) => ({ value, label: value }))


interface Props {
    onFinish: (d: unknown) => Promise<void>
}

export default function Filter({ onFinish: propsOnFinish }: Props) {

    const [loading, setLoading] = useState(false)
    const [form] = Form.useForm();

    const onFinish = async () => {
        try {
            setLoading(true)
            await form.validateFields()
            await propsOnFinish(form.getFieldsValue())
            setLoading(false)
        } catch {
            setLoading(false)
        }
    }

    return (
        <Form
            form={form}
            className='!text-large'
            initialValues={{
                days: 10,
                bar: "5m",
                initial_balance: 10000,
                instId: "BTC-USDT",
                open_fee_rate: 0.0001,
                close_fee_rate: 0.0001,
                leverage: 1,
                maintenance_margin_rate: 0.005,
                min_unit: 10,
                strategy_key: 'ma20',
                currency: 'BTC-USDT',
            }}
        >
            <div className='p-4 border-[1px] border-gray-400 border-dashed rounded-md mb-2'>
                <Row gutter={24}>
                    <Col span={6}>
                        <Form.Item label="选择策略" name="strategy_key">
                            <Select options={Strategy} />
                        </Form.Item>
                    </Col>
                    <Col span={6}>
                        <Form.Item label="K线周期" name="bar">
                            <Select options={Period} />
                        </Form.Item>
                    </Col>
                    <Col span={6}>
                        <Form.Item label="最小下单单位" name="min_unit">
                            <Input placeholder="Basic usage" />
                        </Form.Item>
                    </Col>
                    <Col span={6}>
                        <Form.Item label="币种" name="currency">
                            <Input placeholder="（如BTC- USDT）" />
                        </Form.Item>
                    </Col>
                </Row>
                <Row gutter={24}>
                    <Col span={8}>
                        <Form.Item label="回测天数" name="days">
                            <Slider marks={{ 1: '1', 30: '30' }} min={1} max={30} />
                        </Form.Item>
                    </Col>
                    <Col span={8}>
                        <Form.Item label="初始资金" name="initial_balance">
                            <Slider marks={{ 1000: '1000', 20000: '20000' }} min={1000} max={20000} />
                        </Form.Item>
                    </Col>
                    <Col span={8}>
                        <Form.Item label="杠杆倍数" name="leverage" className='!mb-0'>
                            <Slider marks={{ 1: '1', 20: '20' }} min={1} max={20} />
                        </Form.Item>
                    </Col>
                </Row>
                <Row gutter={24}>
                    <Col span={8}>
                        <Form.Item label="维持保证金率" name="maintenance_margin_rate" className='!mb-0'>
                            <Slider marks={{ 0: '0', 0.1: '0.1' }} step={0.0001} min={0} max={0.1} />
                        </Form.Item>
                    </Col>
                    <Col span={8}>
                        <Form.Item label="开仓手续费率" name="open_fee_rate">
                            <Slider marks={{ 0: '0', 0.01: '0.01' }} step={0.0001} min={0} max={0.01} />
                        </Form.Item>
                    </Col>
                    <Col span={8}>
                        <Form.Item label="平仓手续费率" name="close_fee_rate" className='!mb-0'>
                            <Slider marks={{ 0: '0', 0.01: '0.01' }} step={0.0001} min={0} max={0.01} />
                        </Form.Item>
                    </Col>
                </Row>
            </div>
            <Row gutter={24}>
                <Col span={24}>
                    <Form.Item>
                        <Button type="primary" style={{ width: '100%' }} loading={loading} onClick={onFinish}>提交</Button>
                    </Form.Item>
                </Col>
            </Row>
        </Form>
    )
}