import {afterEach,describe,expect,it,vi} from "vitest";
import {api,request} from "./api";
afterEach(()=>vi.unstubAllGlobals());
describe("OOSYS API client",()=>{
 it("sends bearer credentials to protected endpoints",async()=>{const f=vi.fn().mockResolvedValue(new Response(JSON.stringify({user_id:"u1"}),{status:200,headers:{"Content-Type":"application/json"}}));vi.stubGlobal("fetch",f);await expect(api.me("opaque")).resolves.toEqual({user_id:"u1"});expect(f.mock.calls[0][0]).toBe("/api/v1/auth/me");expect(f.mock.calls[0][1].headers.get("Authorization")).toBe("Bearer opaque");});
 it("surfaces safe API errors",async()=>{vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:"Insufficient permission"}),{status:403})));await expect(request("/private","token")).rejects.toMatchObject({status:403,message:"Insufficient permission"});});
 it("handles no-content responses",async()=>{vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(null,{status:204})));await expect(request("/auth/logout","token",{method:"POST"})).resolves.toBeUndefined();});
 it("does not attach a token to login",async()=>{const f=vi.fn().mockResolvedValue(new Response(JSON.stringify({access_token:"x"}),{status:200}));vi.stubGlobal("fetch",f);await api.login("a@example.com","password");expect(f.mock.calls[0][1].headers.has("Authorization")).toBe(false);});
});