import { useEffect, useRef } from 'react'
import { createChart, type IChartApi, CandlestickSeries, HistogramSeries, LineSeries, ColorType } from 'lightweight-charts'
import type { OHLCVBar, MAData } from '../api/client'

interface Props {
  bars: OHLCVBar[]
  mas: MAData[]
  width?: number
  height?: number
}

export function StockChart({ bars, mas, height = 500 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!containerRef.current || bars.length === 0) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1e293b' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#334155' },
        horzLines: { color: '#334155' },
      },
      width: containerRef.current.clientWidth,
      height,
      crosshair: {
        mode: 0,
      },
      timeScale: {
        borderColor: '#334155',
      },
    })
    chartRef.current = chart

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderDownColor: '#ef4444',
      borderUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      wickUpColor: '#22c55e',
    })

    candleSeries.setData(
      bars.map((b) => ({
        time: b.date,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }))
    )

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    volumeSeries.setData(
      bars.map((b) => ({
        time: b.date,
        value: b.volume,
        color: b.close >= b.open ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)',
      }))
    )

    if (mas.length > 0) {
      const ma20Series = chart.addSeries(LineSeries, { color: '#a855f7', lineWidth: 1 })
      const ma60Series = chart.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 1 })
      const ema120Series = chart.addSeries(LineSeries, { color: '#f97316', lineWidth: 1 })

      ma20Series.setData(
        mas.filter((m) => m.ma20 != null).map((m) => ({ time: m.date, value: m.ma20! }))
      )
      ma60Series.setData(
        mas.filter((m) => m.ma60 != null).map((m) => ({ time: m.date, value: m.ma60! }))
      )
      ema120Series.setData(
        mas.filter((m) => m.ema120 != null).map((m) => ({ time: m.date, value: m.ema120! }))
      )
    }

    chart.timeScale().fitContent()

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [bars, mas, height])

  return <div ref={containerRef} className="w-full rounded-xl overflow-hidden" />
}
