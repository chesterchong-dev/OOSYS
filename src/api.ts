export type Principal={user_id:string;email:string;organization_id:string;membership_id:string;permissions:string[]};
export type Organization={id:string;name:string;slug:string;status:string};
export type Member={membership_id:string;status:string;user:{id:string;email:string;full_name:string;is_active:boolean}};
export type Role={id:string;organization_id:string;name:string;description:string;is_system:boolean};
export type Permission={key:string;description:string};
export type Unit={id:string;organization_id:string;unit_type:string;name:string;code:string|null;parent_id:string|null;status:string};
export type AuditEvent={id:string;actor_user_id:string|null;action:string;target_type:string;target_id:string|null;outcome:string;correlation_id:string|null;created_at:string};
export type Page<T>={items:T[];limit:number;offset:number};
export type InventoryCategory={id:string;organization_id:string;code:string;name:string;archived_at:string|null};
export type InventoryUnit={id:string;organization_id:string;code:string;name:string;decimal_places:number;archived_at:string|null};
export type InventoryProduct={id:string;organization_id:string;sku:string;name:string;description:string;category_id:string|null;unit_id:string;unit_code:string;unit_name:string;barcode:string|null;tracking_mode:"none"|"lot"|"serial";cost_currency:string;average_cost:string;archived_at:string|null;created_at:string;updated_at:string};
export type InventoryBalance={product_id:string;sku:string;product_name:string;unit_code:string;on_hand:string;reserved:string;available:string;average_cost:string;cost_currency:string;version:number};
export type InventoryMovement={id:string;organization_id:string;product_id:string;movement_type:string;quantity_delta:string;reserved_delta:string;unit_cost:string|null;currency_code:string;idempotency_key:string;lot_code:string|null;serial_code:string|null;expires_at:string|null;note:string;actor_user_id:string;created_at:string};
export type InventoryCountLine={id:string;product_id:string;expected_on_hand:string;counted_quantity:string;variance:string;balance_version:number;reason_code:string;reason_note:string};
export type InventoryCount={id:string;organization_id:string;count_number:string;count_type:string;status:string;note:string;created_by_user_id:string;submitted_by_user_id:string|null;approved_by_user_id:string|null;created_at:string;submitted_at:string|null;approved_at:string|null;lines:InventoryCountLine[]};
export type LoginResult={access_token?:string;requires_organization_selection?:boolean;organizations?:{id:string}[]};
const base=(import.meta.env.VITE_API_BASE_URL??"/api/v1").replace(/\/$/,"");
export class ApiError extends Error{constructor(public status:number,message:string){super(message);this.name="ApiError";}}
export async function request<T>(path:string,token?:string|null,init:RequestInit={}):Promise<T>{
 const headers=new Headers(init.headers);headers.set("Accept","application/json");
 if(init.body!==undefined&&!headers.has("Content-Type"))headers.set("Content-Type","application/json");
 if(token)headers.set("Authorization","Bearer "+token);
 const response=await fetch(base+path,{...init,headers});
 if(!response.ok){let message="Request failed ("+response.status+")";try{const body=await response.json() as {detail?:unknown;message?:unknown};if(typeof body.detail==="string")message=body.detail;else if(typeof body.message==="string")message=body.message;}catch{}throw new ApiError(response.status,message);}
 if(response.status===204)return undefined as T;
 const text=await response.text();return (text?JSON.parse(text):undefined) as T;
}
const orgPath=(id:string)=>"/organizations/"+encodeURIComponent(id);
export const api={
 login:(email:string,password:string,organization_id?:string)=>request<LoginResult>("/auth/login",null,{method:"POST",body:JSON.stringify({email,password,...(organization_id?{organization_id}:{})})}),
 me:(t:string)=>request<Principal>("/auth/me",t),logout:(t:string)=>request<void>("/auth/logout",t,{method:"POST"}),
 organization:(t:string,id:string)=>request<Organization>(orgPath(id),t),
 updateOrganization:(t:string,id:string,b:{name:string;status:string})=>request<Organization>(orgPath(id),t,{method:"PATCH",body:JSON.stringify(b)}),
 archiveOrganization:(t:string,id:string)=>request<void>(orgPath(id)+"/archive",t,{method:"POST"}),
 members:(t:string,id:string,offset=0)=>request<Page<Member>>(orgPath(id)+"/members?limit=50&offset="+offset,t),
 updateMember:(t:string,id:string,user:string,b:{status?:string;role_id?:string})=>request<{membership_id:string;status:string}>(orgPath(id)+"/members/"+encodeURIComponent(user),t,{method:"PATCH",body:JSON.stringify(b)}),
 invite:(t:string,id:string,email:string,role_id:string)=>request<{message:string}>(orgPath(id)+"/invitations",t,{method:"POST",body:JSON.stringify({email,role_id})}),
 roles:(t:string,id:string)=>request<Role[]>(orgPath(id)+"/roles",t),permissions:(t:string,id:string)=>request<Permission[]>(orgPath(id)+"/permissions",t),
 createRole:(t:string,id:string,b:{name:string;description:string;permissions:string[]})=>request<Role>(orgPath(id)+"/roles",t,{method:"POST",body:JSON.stringify(b)}),
 updateRole:(t:string,id:string,r:string,b:{name:string;description:string})=>request<Role>(orgPath(id)+"/roles/"+encodeURIComponent(r),t,{method:"PATCH",body:JSON.stringify(b)}),
 archiveRole:(t:string,id:string,r:string)=>request<void>(orgPath(id)+"/roles/"+encodeURIComponent(r)+"/archive",t,{method:"POST"}),
 units:(t:string,id:string,offset=0)=>request<Page<Unit>>(orgPath(id)+"/units?limit=50&offset="+offset,t),
 createUnit:(t:string,id:string,b:{unit_type:string;name:string;code:string|null;parent_id:string|null})=>request<Unit>(orgPath(id)+"/units",t,{method:"POST",body:JSON.stringify(b)}),
 updateUnit:(t:string,id:string,u:string,b:{name:string;code:string|null;parent_id:string|null})=>request<Unit>(orgPath(id)+"/units/"+encodeURIComponent(u),t,{method:"PATCH",body:JSON.stringify(b)}),
 archiveUnit:(t:string,id:string,u:string)=>request<void>(orgPath(id)+"/units/"+encodeURIComponent(u)+"/archive",t,{method:"POST"}),
 audit:(t:string,id:string,offset=0)=>request<Page<AuditEvent>>(orgPath(id)+"/audit-events?limit=50&offset="+offset,t),
 changePassword:(t:string,current_password:string,new_password:string)=>request<void>("/auth/me/password",t,{method:"POST",body:JSON.stringify({current_password,new_password})}),
 inventoryCategories:(t:string,id:string)=>request<Page<InventoryCategory>>(orgPath(id)+"/inventory/categories?limit=100",t),
 inventoryUnits:(t:string,id:string)=>request<Page<InventoryUnit>>(orgPath(id)+"/inventory/units?limit=100",t),
 inventoryProducts:(t:string,id:string,search="")=>request<Page<InventoryProduct>>(orgPath(id)+"/inventory/products?limit=100"+(search?"&search="+encodeURIComponent(search):""),t),
 createInventoryCategory:(t:string,id:string,b:{code:string;name:string})=>request<InventoryCategory>(orgPath(id)+"/inventory/categories",t,{method:"POST",body:JSON.stringify(b)}),
 createInventoryUnit:(t:string,id:string,b:{code:string;name:string;decimal_places:number})=>request<InventoryUnit>(orgPath(id)+"/inventory/units",t,{method:"POST",body:JSON.stringify(b)}),
 createInventoryProduct:(t:string,id:string,b:{sku:string;name:string;description:string;category_id:string|null;unit_id:string;barcode:string|null;tracking_mode:"none"|"lot"|"serial";cost_currency:string})=>request<InventoryProduct>(orgPath(id)+"/inventory/products",t,{method:"POST",body:JSON.stringify(b)}),
 updateInventoryProduct:(t:string,id:string,p:string,b:{name?:string;description?:string;category_id?:string|null;barcode?:string|null})=>request<InventoryProduct>(orgPath(id)+"/inventory/products/"+encodeURIComponent(p),t,{method:"PATCH",body:JSON.stringify(b)}),
 archiveInventoryProduct:(t:string,id:string,p:string)=>request<void>(orgPath(id)+"/inventory/products/"+encodeURIComponent(p)+"/archive",t,{method:"POST"}),
 inventoryBalances:(t:string,id:string)=>request<Page<InventoryBalance>>(orgPath(id)+"/inventory/balances?limit=100",t),
 inventoryMovements:(t:string,id:string,p?:string)=>request<Page<InventoryMovement>>(orgPath(id)+"/inventory/movements?limit=100"+(p?"&product_id="+encodeURIComponent(p):""),t),
 inventoryCounts:(t:string,id:string)=>request<Page<InventoryCount>>(orgPath(id)+"/inventory/counts?limit=100",t),
 createInventoryCount:(t:string,id:string,b:{count_type:"cycle"|"full_stocktake";note:string;lines:{product_id:string;counted_quantity:string;reason_code:"no_variance"|"damage"|"loss"|"found"|"data_correction"|"other";reason_note:string}[]})=>request<InventoryCount>(orgPath(id)+"/inventory/counts",t,{method:"POST",body:JSON.stringify(b)}),
 submitInventoryCount:(t:string,id:string,c:string)=>request<InventoryCount>(orgPath(id)+"/inventory/counts/"+encodeURIComponent(c)+"/submit",t,{method:"POST"}),
 approveInventoryCount:(t:string,id:string,c:string)=>request<InventoryCount>(orgPath(id)+"/inventory/counts/"+encodeURIComponent(c)+"/approve",t,{method:"POST"}),
 rejectInventoryCount:(t:string,id:string,c:string)=>request<InventoryCount>(orgPath(id)+"/inventory/counts/"+encodeURIComponent(c)+"/reject",t,{method:"POST"}),
 createInventoryMovement:(t:string,id:string,b:{product_id:string;movement_type:"receipt"|"issue"|"adjustment"|"count"|"reserve"|"release";quantity:string;direction?:"increase"|"decrease";unit_cost?:string;idempotency_key:string;lot_code?:string;serial_code?:string;expires_at?:string;note?:string})=>request<InventoryMovement>(orgPath(id)+"/inventory/movements",t,{method:"POST",body:JSON.stringify(b)})
};
