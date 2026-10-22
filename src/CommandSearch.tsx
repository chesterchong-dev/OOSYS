import {useState,type KeyboardEvent} from "react";
import {ArrowRight,Search} from "lucide-react";
export type CommandItem={id:string;label:string};
export function CommandSearch({commands,onSelect}:{commands:CommandItem[];onSelect:(id:string)=>void}){
 const [query,setQuery]=useState("");
 const matches=query.trim()?commands.filter(c=>c.label.toLowerCase().includes(query.trim().toLowerCase())).slice(0,6):[];
 function choose(id:string){onSelect(id);setQuery("");}
 function keyDown(e:KeyboardEvent<HTMLInputElement>){if(e.key==="Escape")setQuery("");if(e.key==="Enter"&&matches[0]){e.preventDefault();choose(matches[0].id);}}
 return <div className="command-search"><label htmlFor="command-search-input" className="sr-only">Search workspace commands</label><div className="command-input"><Search size={15}/><input id="command-search-input" type="search" value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={keyDown} placeholder="Search commands…"/><kbd>Enter</kbd></div>{matches.length>0&&<div className="command-results" role="group" aria-label="Command results">{matches.map(c=><button type="button" key={c.id} onClick={()=>choose(c.id)}>{c.label}<ArrowRight size={14}/></button>)}</div>}</div>;
}
