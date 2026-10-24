import type {Organization,Principal} from "./api";
import type {View} from "./App";
import {Overview} from "./Overview";
import {Members} from "./Members";
import {Roles} from "./Roles";
import {OrganizationSettings} from "./Organization";
import {Structure} from "./Structure";
import {Audit} from "./Audit";
import {Profile} from "./Profile";
import {Inventory} from "./Inventory";
export function Workspace({view,token,principal,organization,refreshKey,onMutation,onError}:{view:View;token:string;principal:Principal;organization:Organization;refreshKey:number;onMutation:(s:string)=>void;onError:(e:unknown)=>void}){
const shared={token,principal,organization,refreshKey,onMutation,onError};
switch(view){case "overview":return <Overview token={token} principal={principal} organization={organization} refreshKey={refreshKey} onNavigate={v=>window.dispatchEvent(new CustomEvent("oosys:navigate",{detail:v}))}/>;case "members":return <Members {...shared}/>;case "roles":return <Roles {...shared}/>;case "organization":return <OrganizationSettings {...shared}/>;case "structure":return <Structure {...shared}/>;case "audit":return <Audit token={token} organization={organization} refreshKey={refreshKey}/>;case "profile":return <Profile token={token} principal={principal} onError={onError}/>;case "inventory":return <Inventory {...shared}/>;}
}

