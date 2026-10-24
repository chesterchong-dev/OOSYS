import {cleanup,fireEvent,render,screen} from "@testing-library/react";
import {afterEach,describe,expect,it,vi} from "vitest";
import {Inventory} from "./Inventory";
import {api,type Organization,type Principal} from "./api";

vi.mock("./api",async importOriginal=>{
 const actual=await importOriginal<typeof import("./api")>();
 return { ...actual, api:{ ...actual.api,
  inventoryCategories:vi.fn().mockResolvedValue({items:[],limit:100,offset:0}),
  inventoryUnits:vi.fn().mockResolvedValue({items:[],limit:100,offset:0}),
  inventoryProducts:vi.fn().mockResolvedValue({items:[],limit:100,offset:0}),
  inventoryBalances:vi.fn().mockResolvedValue({items:[],limit:100,offset:0}),
  inventoryReconciliation:vi.fn().mockResolvedValue({items:[],limit:100,offset:0,product_count:0,mismatch_count:0,reconciled:true}),
  inventoryMovements:vi.fn().mockResolvedValue({items:[],limit:100,offset:0}),
  inventoryCounts:vi.fn().mockResolvedValue({items:[],limit:100,offset:0}),
 },
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

 it("shows the separate count review workflow only to users with count permissions",async()=>{
  const countOwner={...principal,permissions:[...principal.permissions,"inventory.counts.read","inventory.counts.write"]};
  render(<Inventory token="session" principal={countOwner} organization={organization} refreshKey={0} onMutation={vi.fn()} onError={vi.fn()}/>);
  expect(await screen.findByRole("heading",{name:"Submit a stock count"})).toBeInTheDocument();
  expect(screen.getByText("No counts yet")).toBeInTheDocument();
  expect(api.inventoryCounts).toHaveBeenCalledWith("session",organization.id);
 });

 it("shows ledger reconciliation mismatches without changing stock",async()=>{
  vi.mocked(api.inventoryReconciliation).mockResolvedValue({items:[{
   product_id:"product-1",sku:"P-100",product_name:"Bearing",balance_exists:true,
   ledger_on_hand:"4.000000",balance_on_hand:"5.000000",ledger_reserved:"0.000000",
   balance_reserved:"0.000000",reconciled:false,
  }],limit:100,offset:0,product_count:1,mismatch_count:1,reconciled:false});
  render(<Inventory token="session" principal={principal} organization={organization} refreshKey={0} onMutation={vi.fn()} onError={vi.fn()}/>);
  expect(await screen.findByRole("heading",{name:"Ledger reconciliation"})).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button",{name:"Check balances"}));
  expect(await screen.findByRole("status")).toHaveTextContent("1 of 1 product balances do not match the ledger.");
  expect(screen.getByText("4.000000")).toBeInTheDocument();
  expect(screen.getByText("5.000000")).toBeInTheDocument();
  expect(api.inventoryReconciliation).toHaveBeenCalledWith("session",organization.id,0);
 });
});

