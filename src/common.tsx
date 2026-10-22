import {useEffect,useState,type ReactNode} from "react";
import {CircleAlert,RefreshCw} from "lucide-react";
export function Heading({eyebrow,title,detail,action}:{eyebrow:string;title:string;detail:string;action?:ReactNode}){return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{detail}</p></div>{action&&<div className="heading-actions">{action}</div>}</div>;}
export function Button({children,onClick,variant="secondary",disabled,type="button"}:{children:ReactNode;onClick?:()=>void;variant?:"primary"|"secondary"|"danger"|"ghost";disabled?:boolean;type?:"button"|"submit"}){return <button type={type} className={"button button-"+variant} onClick={onClick} disabled={disabled}>{children}</button>;}
export function Loading(){return <div className="loading-state" role="status"><span className="spinner"/>Loading data from OOSYS API…</div>;}
export function ErrorPanel({message,retry}:{message:string;retry:()=>void}){return <div className="inline-error" role="alert"><CircleAlert size={17}/><span>{message}</span><Button onClick={retry}><RefreshCw size={14}/>Retry</Button></div>;}
export function Empty({title,detail}:{title:string;detail:string}){return <div className="empty-state"><CircleAlert size={21}/><strong>{title}</strong><span>{detail}</span></div>;}
export const can=(p:{permissions:string[]},key:string)=>p.permissions.includes(key);
export const readable=(s:string)=>s.split("_").map(v=>v.charAt(0).toUpperCase()+v.slice(1)).join(" ");
export function useLoad<T>(loader:()=>Promise<T>,deps:unknown[]){const [data,setData]=useState<T|null>(null);const [busy,setBusy]=useState(true);const [error,setError]=useState("");useEffect(()=>{let alive=true;setBusy(true);setError("");loader().then(v=>{if(alive)setData(v);}).catch(e=>{if(alive)setError(e instanceof Error?e.message:"Unable to load data.");}).finally(()=>{if(alive)setBusy(false);});return()=>{alive=false;};},deps);return {data,busy,error};}
