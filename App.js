import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [jobs, setJobs] = useState([]);
  const [logs, setLogs] = useState([]);
  const [form, setForm] = useState({ name: '', type: 'hourly', time: '' });

  const fetchJobs = async () => {
    const res = await fetch('http://localhost:8000/jobs');
    const data = await res.json();
    setJobs(data);
  };

  const fetchLogs = async () => {
    const res = await fetch('http://localhost:8000/logs');
    const data = await res.json();
    setLogs(data);
  };

  useEffect(() => {
    fetchJobs();
    fetchLogs();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    await fetch('http://localhost:8000/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    setForm({ name: '', type: 'hourly', time: '' });
    fetchJobs();
  };

  const toggleJob = async (id) => {
    await fetch(`http://localhost:8000/jobs/${id}/toggle`, { method: 'POST' });
    fetchJobs();
  };

const runJobNow = async (id) => {
  try {
    const res = await fetch(`http://localhost:8000/jobs/${id}/run`, {
      method: 'POST',
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(errorText || 'Failed to run job');
    }

    alert('Job triggered successfully!');
    fetchJobs();
    fetchLogs();
  } catch (error) {
    console.error('Error running job:', error);
    alert('Failed to trigger job. See console for more.');
  }
};

  return (
    <div className="App">
      <h2>Job Scheduler</h2>

      <form onSubmit={handleSubmit}>
        <input placeholder="Job Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
          <option value="hourly">Hourly</option>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
        </select>
        <input
          placeholder={
            form.type === 'hourly' ? 'Minute (e.g. 15)' :
            form.type === 'daily' ? 'HH:MM (e.g. 14:30)' :
            'Day HH:MM (e.g. mon 12:45)'
          }
          value={form.time}
          onChange={(e) => setForm({ ...form, time: e.target.value })}
          required
        />
        <button type="submit">Add Job</button>
      </form>

      <h3>Scheduled Jobs</h3>
      <table>
        <thead>
          <tr>
            <th>Name</th><th>Type</th><th>Time</th><th>Enabled</th><th>Last Run</th><th>Next Run</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td>{job.name}</td>
              <td>{job.type}</td>
              <td>{job.time}</td>
              <td>{job.enabled ? '✅' : '❌'}</td>
              <td>{job.last_run ? new Date(job.last_run).toLocaleString() : '-'}</td>
              <td>{job.next_run ? new Date(job.next_run).toLocaleString() : '-'}</td>
              <td>
                <button onClick={() => toggleJob(job.id)}>Toggle</button>
                <button onClick={() => runJobNow(job.id)}>Run Now</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Job Logs</h3>
      <ul>
        {logs.map((log, i) => (
          <li key={i}>
            {new Date(log.run_time).toLocaleString()} — <b>{log.job_name}</b>: {log.output}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
