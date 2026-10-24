import {useCallback,useEffect,useMemo,useState} from "react";
import {Activity,Building2,LayoutDashboard,LogOut,Menu,Network,ShieldCheck,Users,UserRound,X,Boxes} from "lucide-react";
import {api,ApiError,type Organization,type Principal} from "./api";
import {Login} from "./Login";
import {Workspace} from "./Workspace";
import {CommandSearch} from "./CommandSearch";
export type View="overview"|"members"|"roles"|"organization"|"structure"|"audit"|"profile"|"inventory";
const nav:{id:View;label:string;icon:typeof LayoutDashboard;permission?:string}[]=[
{id:"overview",label:"Overview",icon:LayoutDashboard},{id:"members",label:"Members",icon:Users,permission:"members.read"},
{id:"roles",label:"Roles & access",icon:ShieldCheck,permission:"roles.read"},{id:"organization",label:"Organization",icon:Building2,permission:"organization.read"},{id:"inventory",label:"Inventory",icon:Boxes,permission:"inventory.products.read"},
{id:"structure",label:"Structure",icon:Network,permission:"organization.units.read"},{id:"audit",label:"Audit trail",icon:Activity,permission:"audit.read"},{id:"profile",label:"My account",icon:UserRound}];
export default function App(){
const [token,setToken]=useState<string|null>(()=>sessionStorage.getItem("oosys.session"));const [principal,setPrincipal]=useState<Principal|null>(null);const [org,setOrg]=useState<Organization|null>(null);
const [view,setView]=useState<View>("overview");const [notice,setNotice]=useState<{kind:"success"|"error";message:string}|null>(null);const [refreshKey,setRefreshKey]=useState(0);const [mobile,setMobile]=useState(false);const [booting,setBooting]=useState(Boolean(sessionStorage.getItem("oosys.session")));
const clearSession=useCallback(()=>{sessionStorage.removeItem("oosys.session");setToken(null);setPrincipal(null);setOrg(null);setBooting(false);},[]);
useEffect(()=>{if(!token)return;let alive=true;setBooting(true);api.me(token).then(async p=>{const o=await api.organization(token,p.organization_id);if(alive){setPrincipal(p);setOrg(o);setBooting(false);}}).catch(()=>{if(alive)clearSession();});return()=>{alive=false;};},[token,clearSession]);
useEffect(()=>{const clear=()=>clearSession();const navigate=(e:Event)=>setView((e as CustomEvent<View>).detail);const refresh=()=>setRefreshKey(v=>v+1);window.addEventListener("oosys:clear-session",clear);window.addEventListener("oosys:navigate",navigate);window.addEventListener("oosys:refresh",refresh);return()=>{window.removeEventListener("oosys:clear-session",clear);window.removeEventListener("oosys:navigate",navigate);window.removeEventListener("oosys:refresh",refresh);};},[clearSession]);
const permissions=useMemo(()=>new Set(principal?.permissions??[]),[principal]);const links=nav.filter(n=>!n.permission||permissions.has(n.permission));
useEffect(()=>{if(!links.some(n=>n.id===view))setView("overview");},[links,view]);
const login=(value:string)=>{sessionStorage.setItem("oosys.session",value);setToken(value);};
const logout=async()=>{if(token)try{await api.logout(token);}catch{}clearSession();};
const onMutation=(message:string)=>{setNotice({kind:"success",message});setRefreshKey(v=>v+1);};
const onError=(error:unknown)=>{if(error instanceof ApiError&&error.status===401)clearSession();setNotice({kind:"error",message:error instanceof Error?error.message:"Something went wrong."});};
if(booting)return <div className="boot-screen" role="status">Loading your secure workspace…</div>;
if(!token||!principal||!org)return <Login onLogin={login}/>;
const active=links.find(n=>n.id===view)??links[0];const ActiveIcon=active.icon;
return <div className="app-frame">{mobile&&<button className="mobile-scrim" aria-label="Close navigation" onClick={()=>setMobile(false)}/>}
<aside className={"sidebar "+(mobile?"sidebar-open":"")} aria-label="Main navigation"><div className="brand-lockup"><div className="brand-mark">O</div><div><strong>OOSYS</strong><span>ONLY ONE SYSTEM</span></div><button className="icon-button sidebar-close" aria-label="Close navigation" onClick={()=>setMobile(false)}><X size={17}/></button></div>
<div className="workspace-label">WORKSPACE</div><div className="tenant-switcher"><div className="tenant-avatar">{org.name.slice(0,1).toUpperCase()}</div><div className="tenant-copy"><strong>{org.name}</strong><span>{org.slug}</span></div></div>
<nav className="nav-list"><span className="nav-section">YOUR WORKSPACE</span>{links.map(n=>{const Icon=n.icon;return <button key={n.id} className={"nav-item "+(view===n.id?"nav-active":"")} aria-current={view===n.id?"page":undefined} onClick={()=>{setView(n.id);setMobile(false);setNotice(null);}}><Icon size={18}/><span>{n.label}</span></button>;})}</nav>
<div className="sidebar-bottom"><div className="secure-label"><span className="status-dot"/>Secure session</div><div className="user-card"><div className="user-avatar">{principal.email.slice(0,1).toUpperCase()}</div><div className="user-copy"><strong>{principal.email}</strong><span>Signed in</span></div><button className="icon-button" aria-label="Sign out" onClick={logout}><LogOut size={16}/></button></div></div></aside>
<div className="main-column"><header className="topbar"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={()=>setMobile(true)}><Menu size={19}/></button><div className="breadcrumbs"><span>Workspace</span><span>/</span><strong><ActiveIcon size={14}/>{active.label}</strong></div><CommandSearch commands={links.map(n=>({id:n.id,label:n.label}))} onSelect={id=>{setView(id as View);setNotice(null);}}/><span className="live-indicator"><span className="status-dot"/>API connected</span></header>
<main id="main-content" className="main-content">{notice&&<div className={"notice notice-"+notice.kind} role={notice.kind==="error"?"alert":"status"}><span>{notice.message}</span><button className="icon-button" aria-label="Dismiss notification" onClick={()=>setNotice(null)}><X size={15}/></button></div>}
<Workspace view={view} token={token} principal={principal} organization={org} refreshKey={refreshKey} onMutation={onMutation} onError={onError}/>
<footer className="page-footer"><span>OOSYS Platform Foundation</span><span>Tenant-scoped access · Secure by design</span></footer></main></div></div>;
}
