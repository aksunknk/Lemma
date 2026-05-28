import { useState, useEffect, KeyboardEvent } from 'react';

interface InputPanelProps {
  query: string;
  setQuery: (val: string) => void;
  eraMin: number;
  setEraMin: (val: number) => void;
  eraMax: number;
  setEraMax: (val: number) => void;
  origin: number;
  setOrigin: (val: number) => void;
  style: number;
  setStyle: (val: number) => void;
  renown: number;
  setRenown: (val: number) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

export const InputPanel = ({
  query, setQuery,
  eraMin, setEraMin,
  eraMax, setEraMax,
  origin, setOrigin,
  style, setStyle,
  renown, setRenown,
  onSubmit,
  isLoading
}: InputPanelProps) => {

  const otherSliders: { id: string; label: string; sublabel: string; left: string; right: string; value: number; setter: (v: number) => void }[] = [
    { id: 'style',  label: 'Style',  sublabel: '文体',   left: '平易', right: '硬質', value: style,  setter: setStyle },
    { id: 'renown', label: 'Renown', sublabel: '知名度', left: 'ニッチ', right: 'マス', value: renown, setter: setRenown },
  ];

  const handleEraMinChange = (val: number) => {
    setEraMin(val);
    if (val > eraMax) setEraMax(val);
  };

  const handleEraMaxChange = (val: number) => {
    setEraMax(val);
    if (val < eraMin) setEraMin(val);
  };

  // 西暦から座標 (0.0-1.0) への変換
  const yearToCoord = (year: number) => Math.max(0, Math.min(1, (year - 1800) / 230));
  // 座標から西暦への変換
  const coordToYear = (coord: number) => Math.floor(1800 + coord * 230);

  // ローカル入力用ステート（文字列としての自由な入力を許可）
  const [minInput, setMinInput] = useState(coordToYear(eraMin).toString());
  const [maxInput, setMaxInput] = useState(coordToYear(eraMax).toString());

  // スライダー操作時にテキスト入力欄を同期
  useEffect(() => {
    setMinInput(coordToYear(eraMin).toString());
  }, [eraMin]);

  useEffect(() => {
    setMaxInput(coordToYear(eraMax).toString());
  }, [eraMax]);

  // 入力確定時のバリデーション処理
  const commitMinYear = () => {
    let year = parseInt(minInput);
    if (isNaN(year)) year = 1800;
    year = Math.max(1800, Math.min(2030, year));
    handleEraMinChange(yearToCoord(year));
    setMinInput(year.toString());
  };

  const commitMaxYear = () => {
    let year = parseInt(maxInput);
    if (isNaN(year)) year = 2030;
    year = Math.max(1800, Math.min(2030, year));
    handleEraMaxChange(yearToCoord(year));
    setMaxInput(year.toString());
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>, type: 'min' | 'max') => {
    if (e.key === 'Enter') {
      if (type === 'min') commitMinYear();
      else commitMaxYear();
    }
  };

  return (
    <div className="flex flex-col space-y-10 w-full max-w-sm">
      <div className="space-y-10">
        
        {/* QUERY Textarea */}
        <div className="group" id="query-section">
          <label className="block text-sm uppercase tracking-widest text-gray-400 mb-4 transition-colors group-hover:text-gray-300">
            Query / 概念・キーワード
          </label>
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="探索したい概念、あらすじ、またはキーワードを自由に入力..."
            rows={3}
            className="w-full bg-transparent border border-gray-800 rounded-sm p-3 outline-none text-gray-100 placeholder-gray-700 focus:border-gray-500 transition-all tracking-wider resize-none text-sm font-sans"
          />
        </div>

        {/* ERA Range Sliders with Numeric Input */}
        <div className="group" id="era-section">
          <label className="block text-sm uppercase tracking-widest text-gray-400 mb-6 transition-colors group-hover:text-gray-300">
            Era / 年代範囲
          </label>
          
          {/* Min Slider & Input */}
          <div className="flex items-center space-x-8 mb-6">
            <span className="text-[10px] tracking-widest text-gray-500 uppercase leading-none w-10 text-right whitespace-nowrap">START</span>
            <div className="flex-1 flex flex-col items-center">
              <input
                type="range" min="0" max="1" step="0.01" value={eraMin}
                onChange={e => handleEraMinChange(Number(e.target.value))}
                className="w-full h-[2px] bg-gray-800 appearance-none outline-none focus:bg-gray-500 transition-all [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full cursor-pointer hover:bg-gray-700"
              />
              <div className="mt-2 flex items-center text-sm font-bold text-gray-100 font-mono tracking-widest">
                <input
                  type="number"
                  value={minInput}
                  onChange={e => setMinInput(e.target.value)}
                  onBlur={commitMinYear}
                  onKeyDown={e => handleKeyDown(e, 'min')}
                  className="bg-transparent text-right w-12 outline-none text-[#e0e0e0] font-mono appearance-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none m-0 [appearance:textfield]"
                />
                <span className="ml-1">年</span>
              </div>
            </div>
            <div className="w-10"></div>
          </div>

          {/* Max Slider & Input */}
          <div className="flex items-center space-x-8">
            <span className="text-[10px] tracking-widest text-gray-500 uppercase leading-none w-10 text-right whitespace-nowrap">END</span>
            <div className="flex-1 flex flex-col items-center">
              <input
                type="range" min="0" max="1" step="0.01" value={eraMax}
                onChange={e => handleEraMaxChange(Number(e.target.value))}
                className="w-full h-[2px] bg-gray-800 appearance-none outline-none focus:bg-gray-500 transition-all [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full cursor-pointer hover:bg-gray-700"
              />
              <div className="mt-2 flex items-center text-sm font-bold text-gray-100 font-mono tracking-widest">
                <input
                  type="number"
                  value={maxInput}
                  onChange={e => setMaxInput(e.target.value)}
                  onBlur={commitMaxYear}
                  onKeyDown={e => handleKeyDown(e, 'max')}
                  className="bg-transparent text-right w-12 outline-none text-[#e0e0e0] font-mono appearance-none [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none m-0 [appearance:textfield]"
                />
                <span className="ml-1">年</span>
              </div>
            </div>
            <div className="w-10"></div>
          </div>
        </div>

        {/* ORIGIN Toggle UI */}
        <div className="group" id="origin-section">
          <label className="block text-sm uppercase tracking-widest text-gray-400 mb-6 transition-colors group-hover:text-gray-300">
            Origin / 属性
          </label>
          <div className="flex items-center justify-between p-1 bg-gray-900/50 border border-gray-800 rounded-sm">
            <button
              onClick={() => setOrigin(0.0)}
              className={`flex-1 py-3 text-xs tracking-[0.3em] font-bold uppercase transition-all duration-300 ${
                origin === 0.0 
                  ? 'bg-gray-800 text-white border border-gray-600 shadow-lg translate-y-[-2px]' 
                  : 'text-gray-600 hover:text-gray-400 opacity-50'
              }`}
            >
              国内
            </button>
            <div className="w-[1px] h-4 bg-gray-800 mx-2"></div>
            <button
              onClick={() => setOrigin(1.0)}
              className={`flex-1 py-3 text-xs tracking-[0.3em] font-bold uppercase transition-all duration-300 ${
                origin === 1.0 
                  ? 'bg-gray-800 text-white border border-gray-600 shadow-lg translate-y-[-2px]' 
                  : 'text-gray-600 hover:text-gray-400 opacity-50'
              }`}
            >
              海外
            </button>
          </div>
        </div>

        {/* Other Sliders (Style, Renown) */}
        {otherSliders.map((s) => (
          <div key={s.id} className="group" id={`${s.id}-section`}>
            <label className="block text-sm uppercase tracking-widest text-gray-400 mb-6 transition-colors group-hover:text-gray-300">
              {s.label} / {s.sublabel}
            </label>
            <div className="flex items-center space-x-8">
              <span className="text-sm tracking-widest text-gray-500 uppercase leading-none w-10 text-right whitespace-nowrap">{s.left}</span>
              <div className="flex-1 flex flex-col items-center">
                <input
                  id={`${s.id}-slider`}
                  type="range" min="0" max="1" step="0.05" value={s.value}
                  onChange={e => s.setter(Number(e.target.value))}
                  className="w-full h-[2px] bg-gray-800 appearance-none outline-none focus:bg-gray-500 transition-all [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full cursor-pointer hover:bg-gray-700"
                />
                <span className="mt-2 text-xl font-bold text-gray-100 font-mono tracking-widest">{s.value.toFixed(2)}</span>
              </div>
              <span className="text-sm tracking-widest text-gray-500 uppercase leading-none w-10 whitespace-nowrap">{s.right}</span>
            </div>
          </div>
        ))}
      </div>

      {/* 抽出ボタン */}
      <div className="pt-8 flex justify-center flex-col items-center">
        <button
          id="extract-btn"
          onClick={onSubmit}
          disabled={isLoading}
          className="relative inline-flex items-center justify-center w-full py-6 text-base font-bold tracking-[0.5em] text-gray-100 bg-transparent border-2 border-gray-500 hover:border-white transition-all duration-700 hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed uppercase"
        >
          {isLoading ? '解析中...' : '空間を検索'}
        </button>
      </div>
    </div>
  );
};
