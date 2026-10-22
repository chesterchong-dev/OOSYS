import {fireEvent,render,screen} from "@testing-library/react";
import {describe,expect,it,vi} from "vitest";
import {CommandSearch} from "./CommandSearch";
describe("Command search accessibility and navigation",()=>{
 it("offers labelled search and navigates to matching permitted commands",()=>{const onSelect=vi.fn();render(<CommandSearch commands={[{id:"members",label:"Members"},{id:"audit",label:"Audit trail"}]} onSelect={onSelect}/>);const input=screen.getByRole("searchbox",{name:"Search workspace commands"});fireEvent.change(input,{target:{value:"audit"}});fireEvent.click(screen.getByRole("button",{name:"Audit trail"}));expect(onSelect).toHaveBeenCalledWith("audit");expect(input).toHaveValue("");});
 it("supports keyboard selection and escape",()=>{const onSelect=vi.fn();render(<CommandSearch commands={[{id:"roles",label:"Roles & access"}]} onSelect={onSelect}/>);const input=screen.getByRole("searchbox",{name:"Search workspace commands"});fireEvent.change(input,{target:{value:"role"}});fireEvent.keyDown(input,{key:"Enter"});expect(onSelect).toHaveBeenCalledWith("roles");fireEvent.change(input,{target:{value:"role"}});fireEvent.keyDown(input,{key:"Escape"});expect(input).toHaveValue("");});
});
