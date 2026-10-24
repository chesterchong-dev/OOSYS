import {cleanup,render,screen} from "@testing-library/react";
import {afterEach,describe,expect,it,vi} from "vitest";
import {Inventory} from "./Inventory";
import {api,type Organization,type Principal} from "./api";

vi.mock("./api",async importOriginal=>{
 const actual=await importOriginal<typeof import("./api")>();
 return { ...actual,
  inventoryCategories:vi.fn().mockResolvedValue({items:[],limit:100,offset:0}),
  inventoryUnits:vi.fn().mockResolvedValue({items:[],limit:100,offset:0}),
  inventoryProducts:vi.fn().mockResolvedValue({items:[],limit:100,offset:0}),
  inventoryBalances:vi.fn().mockResolvedValue({items:[],limit:100,offset:0}),
  inventoryMovements:vi.fn().mockResolvedValue({items:[],limit:100,offset:0}),
 };
});
afterEach(()=>{cleanup();vi.clearAllMocks();});

const organization:Organization={id:"org-1",name:"Test Organization",slug:"test-org",status:"active"};
const principal:Principal={user_id:"user-1",email:"owner@example.com",organization_id:organization.id,membership_id:"membership-1",permissions:["inventory.products.read","inventory.products.write","inventory.stock.read","inventory.stock.write"]};

describe("Inventory screen",()=>{
 it("loads tenant-scoped catalog and ledger views and explains the first setup step",async()=>{
  render(<Inventory token="session" principal={principal} organization={organization} refreshKey={0} onMutation={vi.fn()} onError={vi.fn()}/>);
  expect(await screen.findByRole("heading",{name:"Products and stock"})).toBeInTheDocument();
  expect(screen.getByText("No products yet")).toBeInTheDocument();
  expect(api.inventoryCategories).toHaveBeenCalledWith("session",organization.id);
  expect(api.inventoryUnits).toHaveBeenCalledWith("session",organization.id);
  expect(api.inventoryProducts).toHaveBeenCalledWith("session",organization.id,"");
  expect(api.inventoryBalances).toHaveBeenCalledWith("session",organization.id);
 });

 it("hides product mutations from users with read-only inventory permission",async()=>{
  const reader={...principal,permissions:["inventory.products.read"]};
  render(<Inventory token="session" principal={reader} organization={organization} refreshKey={0} onMutation={vi.fn()} onError={vi.fn()}/>);
  expect(await screen.findByRole("heading",{name:"Products and stock"})).toBeInTheDocument();
  expect(screen.queryByRole("heading",{name:"Add a stockable product"})).not.toBeInTheDocument();
  expect(api.inventoryBalances).not.toHaveBeenCalled();
 });
});

