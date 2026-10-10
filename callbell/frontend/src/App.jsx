import { Link, Route, Routes } from 'react-router-dom'
import { DEPARTMENTS } from './api'
import Admin from './pages/Admin'
import Bedside from './pages/Bedside'
import DeptQueue from './pages/DeptQueue'

// Demo role picker (no login for the hackathon)
function Home() {
  return (
    <main className="home">
      <p className="eyebrow">RUHack · Challenge 2</p>
      <h1>AI Call Bell Router</h1>
      <p className="lede">Patients ask in their own words. Requests go to the right team, and nurses get the clinical ones.</p>
      <div className="home-grid">
        <Link className="home-card home-patient" to="/bed/412B"><span>🛏️</span>Patient bedside<small>Bed 412B</small></Link>
        {DEPARTMENTS.map((d) => (
          <Link key={d.id} className={`home-card ${d.id === 'nursing' ? 'home-nursing' : ''}`} to={`/dept/${d.id}`}>
            <span>{d.icon}</span>{d.label}<small>Queue</small>
          </Link>
        ))}
        <Link className="home-card" to="/admin"><span>⚙️</span>Admin<small>Rooms & beds</small></Link>
      </div>
    </main>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/bed/:bedId" element={<Bedside />} />
      <Route path="/dept/:dept" element={<DeptQueue />} />
      <Route path="/admin" element={<Admin />} />
    </Routes>
  )
}
