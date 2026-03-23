import React, { useEffect, useRef, useState } from 'react';
import { createChart, CrosshairMode } from 'lightweight-charts';
import axios from 'axios';
import { Loader2 } from 'lucide-react';

const PaperTradingChart = ({ symbol, positions }) => {
  const chartContainerRef = useRef(null);
  const chartInstanceRef = useRef(null);
  const candleSeriesRef = useRef(null);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    
    const fetchAndRenderChart = async () => {
      if (!symbol || !chartContainerRef.current) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const res = await axios.get(`http://127.0.0.1:8000/api/paper-trader/klines?symbol=${symbol}&limit=100`);
        
        if (!isMounted) return;
        
        if (res.data.status === 'success' && res.data.data.length > 0) {
          const chartData = res.data.data;
          
          // Cleanup previous chart instance
          if (chartInstanceRef.current) {
            chartInstanceRef.current.remove();
          }

          // Initialize lightweight-chart
          const chart = createChart(chartContainerRef.current, {
            layout: {
              background: { type: 'solid', color: 'transparent' },
              textColor: '#9ca3af',
            },
            grid: {
              vertLines: { color: 'rgba(55, 65, 81, 0.3)' },
              horzLines: { color: 'rgba(55, 65, 81, 0.3)' },
            },
            crosshair: {
              mode: CrosshairMode.Normal,
            },
            rightPriceScale: {
              borderColor: 'rgba(55, 65, 81, 0.5)',
            },
            timeScale: {
              borderColor: 'rgba(55, 65, 81, 0.5)',
              timeVisible: true,
            },
            autoSize: true, // Make it responsive
          });
          
          chartInstanceRef.current = chart;

          const candlestickSeries = chart.addCandlestickSeries({
            upColor: '#10b981', // green-500
            downColor: '#ef4444', // red-500
            borderVisible: false,
            wickUpColor: '#10b981',
            wickDownColor: '#ef4444',
          });
          
          candleSeriesRef.current = candlestickSeries;
          candlestickSeries.setData(chartData);
          
          // Draw horizontal lines for active positions
          const position = positions?.find(p => p.symbol === symbol);
          if (position && position.entry_price) {
            const isLong = position.side.toUpperCase() === 'LONG';
            const color = isLong ? '#10b981' : '#ef4444';
            
            candlestickSeries.createPriceLine({
              price: position.entry_price,
              color: color,
              lineWidth: 2,
              lineStyle: 2, // Dashed
              axisLabelVisible: true,
              title: `${position.side} Entry`,
            });
          }

          chart.timeScale().fitContent();
        } else {
          setError('No data available for ' + symbol);
        }
      } catch (err) {
        if (isMounted) setError('Failed to fetch chart data');
        console.error(err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchAndRenderChart();

    return () => {
      isMounted = false;
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
        chartInstanceRef.current = null;
      }
    };
  }, [symbol, positions]);

  // Handle auto-resizing
  useEffect(() => {
    const handleResize = () => {
      if (chartInstanceRef.current && chartContainerRef.current) {
        chartInstanceRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight
        });
      }
    };
    
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (!symbol) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Select a position to view chart
      </div>
    );
  }

  return (
    <div className="relative w-full h-full min-h-[300px]">
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-gray-900/50 backdrop-blur-sm">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      )}
      
      {error && (
        <div className="absolute inset-0 z-10 flex items-center justify-center text-red-400">
          {error}
        </div>
      )}
      
      {/* Target for lightweight-charts rendering */}
      <div ref={chartContainerRef} className="w-full h-full absolute inset-0" />
      
      {/* Absolute positioned info overlay */}
      {!loading && !error && (
        <div className="absolute top-4 left-4 z-10 bg-gray-900/80 p-2 rounded border border-gray-700 pointer-events-none">
          <span className="font-bold text-gray-200">{symbol}</span>
          <span className="text-xs text-gray-400 ml-2">1h timeframe</span>
        </div>
      )}
    </div>
  );
};

export default PaperTradingChart;
