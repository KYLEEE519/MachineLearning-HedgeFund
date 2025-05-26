// import { Client } from "@gradio/client";
import { data } from './data'

export async function GET() {
  // const client = await Client.connect("http://127.0.0.1:7860/");
  // const data = await client.predict(
  //   "/run_and_return", {
  //     strategy_key: "ma20",
  //     strategy_param_json: JSON.stringify({
  //       ma_length: 20,
  //       position_ratio: 0.5
  //     }),
  //     days: 10,
  //     bar: "5m",
  //     initial_balance: 10000,
  //     instId: "BTC-USDT",
  //     show_charts: true,
  //     open_fee_rate: 0.0025,
  //     close_fee_rate: 0.0014,
  //     leverage: 7,
  //     maintenance_margin_rate: 0.03,
  //     min_unit: 10,
  //     allow_multiple_positions: false,
  //   }
  // )
 
  return Response.json(data)
}