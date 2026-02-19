import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { CommandCenter } from './pages/CommandCenter'
import { Positions } from './pages/Positions'
import { Opportunities } from './pages/Opportunities'
import { Chart } from './pages/Chart'

function NavBar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive ? 'bg-[var(--color-surface-hover)] text-white' : 'text-[var(--color-text-secondary)] hover:text-white'
    }`

  return (
    <nav className="border-b px-6 py-3 flex items-center gap-2" style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
      <span className="text-lg font-bold mr-6">LEI</span>
      <NavLink to="/" className={linkClass}>指令</NavLink>
      <NavLink to="/positions" className={linkClass}>持仓</NavLink>
      <NavLink to="/opportunities" className={linkClass}>机会</NavLink>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg)' }}>
        <NavBar />
        <Routes>
          <Route path="/" element={<CommandCenter />} />
          <Route path="/positions" element={<Positions />} />
          <Route path="/opportunities" element={<Opportunities />} />
          <Route path="/chart/:symbol" element={<Chart />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
