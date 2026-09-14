import React from 'react';

export function Icon({name}) {
  const common = {viewBox:'0 0 24 24', fill:'none', stroke:'currentColor', strokeWidth:'1.8', strokeLinecap:'round', strokeLinejoin:'round', 'aria-hidden':'true'};
  const paths = {
    home: <><path d="M4 11.5 12 4l8 7.5"/><path d="M6.5 10.5V20h11V10.5"/></>,
    office: <><rect x="4" y="8" width="16" height="12" rx="1.5"/><path d="M9 20V12h6v8M4 8l8-4 8 4"/></>,
    holding: <><path d="M4 20V8l8-4 8 4v12"/><path d="M9 20v-6h6v6"/></>,
    company: <><rect x="3" y="10" width="7" height="10"/><rect x="12" y="4" width="9" height="16"/><path d="M5.5 13h2M5.5 16h2M15 8h3M15 12h3M15 16h3"/></>,
    floors: <><path d="M4 20V7l8-3 8 3v13"/><path d="M4 11h16M4 15.5h16M12 4v16"/></>,
    missions: <><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></>,
    evidence: <><path d="M7 4h7l6 6v10a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path d="M14 4v6h6"/></>,
    knowledge: <><path d="M5 5h6a3 3 0 0 1 3 3v11H8a3 3 0 0 0-3 3V5z"/><path d="M19 5h-6a3 3 0 0 0-3 3v11h6a3 3 0 0 1 3 3V5z"/></>,
    reports: <><path d="M5 19V9M10 19V5M15 19v-7M20 19V8"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M12 3v2M12 19v2M5 12H3M21 12h-2M6.2 6.2l1.4 1.4M16.4 16.4l1.4 1.4M17.8 6.2l-1.4 1.4M7.6 16.4 6.2 17.8"/></>,
    mail: <><rect x="3" y="6" width="18" height="12" rx="2"/><path d="m3 8 9 6 9-6"/></>,
    chat: <><path d="M5 18v-8a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v4a5 5 0 0 1-5 5H8l-3 3z"/></>,
    communications: <><rect x="3" y="5" width="11" height="8" rx="1.5"/><path d="m3 7 5.5 3.5L14 7M16 11h5M16 15h4M8 16h5"/></>,
    calendar: <><rect x="4" y="6" width="16" height="14" rx="2"/><path d="M8 4v4M16 4v4M4 11h16"/></>,
    decisions: <><path d="M9 11.5 11.2 14 16 8"/><circle cx="12" cy="12" r="8"/></>,
    agents: <><circle cx="9" cy="8" r="3"/><path d="M4 19a5 5 0 0 1 10 0"/><circle cx="17" cy="9" r="2.4"/><path d="M14.5 19a4.2 4.2 0 0 1 6.2-3.4"/></>,
    alert: <><path d="M12 4 3.5 19h17L12 4z"/><path d="M12 10v5M12 17.5v.5"/></>,
    chevron: <><path d="m9 6 6 6-6 6"/></>,
    upload: <><path d="M12 16V7"/><path d="m8 11 4-4 4 4"/><path d="M5 19h14"/></>,
    activity: <><circle cx="6" cy="12" r="2"/><circle cx="12" cy="7" r="2"/><circle cx="18" cy="16" r="2"/><path d="M8 12h2.5L13 8.5 16 14"/></>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    bell: <><path d="M6 16V10a6 6 0 1 1 12 0v6"/><path d="M5 16h14"/><path d="M10 19a2 2 0 0 0 4 0"/></>,
    search: <><circle cx="11" cy="11" r="6"/><path d="m20 20-3.5-3.5"/></>,
    users: <><circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.2"/><path d="M4 19a5 5 0 0 1 10 0M14.2 19a4 4 0 0 1 6.3-3.2"/></>,
    finance: <><path d="M4 19h16M7 16V9M12 16V6M17 16v-5"/></>,
    instruction: <><path d="M7 4h8l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path d="M15 4v6h6M8 13h8M8 17h5"/></>,
    logout: <><path d="M9 7V5a2 2 0 0 1 2-2h8v18h-8a2 2 0 0 1-2-2v-2"/><path d="M13 12H4m0 0 3-3M4 12l3 3"/></>,
    news: <><path d="M4 5h12v14H6a2 2 0 0 1-2-2V5z"/><path d="M16 8h4v9a2 2 0 0 1-2 2h-2"/><path d="M7 9h6M7 13h6"/></>,
  };
  return <svg {...common}>{paths[name] || paths.home}</svg>;
}

export function Logo() {
  return (
    <svg className="logo-mark" viewBox="0 0 48 48" aria-hidden="true">
      <rect width="48" height="48" rx="14" fill="#163a52"/>
      <rect x="1.2" y="1.2" width="45.6" height="45.6" rx="12.8" fill="#0f2c40"/>
      <path d="M16 13v22h6.2V24.2H30c4.4 0 7-2.3 7-5.6 0-3.4-2.6-5.6-7.1-5.6H16zm6.2 4.8H29c1.9 0 3 .8 3 2.2s-1.1 2.2-3 2.2h-6.8v-4.4z" fill="#f4f7fa"/>
      <path d="M34 15.2 42 10v7.2l-8 5.2z" fill="#c9a24d"/>
    </svg>
  );
}
