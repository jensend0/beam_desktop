"""Beam Designer: a small Tkinter beam analysis desktop application."""
import json
import math
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

SECTIONS = {
    "Steel": {
        "W8x10": (30.8, 7.81, 10), "W10x12": (53.8, 10.9, 12),
        "W12x26": (204, 33.4, 26), "W14x22": (199, 29.0, 22),
        "W16x26": (301, 38.4, 26), "W18x35": (510, 57.6, 35),
        "W21x44": (843, 81.6, 44), "W24x55": (1350, 114, 55)},
    "Douglas Fir-Larch": {
        "2x8": (47.63, 13.14, 0), "2x10": (98.93, 21.39, 0),
        "2x12": (177.98, 31.64, 0)}}
E_MOD = {"Steel": 29000, "Douglas Fir-Larch": 1600}
FB = {"Steel": 30, "Douglas Fir-Larch": .9}
BG, NAVY, BLUE, MUTED = "#f4f7fb", "#17324d", "#2563eb", "#64748b"


def analyze(state, section=None):
    span = float(state["span"])
    support = state["support"]
    points = state["points"]
    uniforms = state["uniforms"]
    total = sum(p["magnitude"] for p in points)
    total += sum(u["magnitude"] * max(0, min(span, u["end"]) - max(0, u["start"])) for u in uniforms)
    if support == "Simply supported":
        left = sum(p["magnitude"] * (span-p["position"]) for p in points)
        left += sum(u["magnitude"] * max(0, min(span,u["end"])-max(0,u["start"])) *
                    (span-(max(0,u["start"])+min(span,u["end"]))/2) for u in uniforms)
        left /= span
        right = total-left
    else:
        left, right = total, 0
    n = max(120, int(span*24))
    xs = sorted(set([span*i/n for i in range(n+1)] + [p["position"] for p in points] +
                    [v for u in uniforms for v in (max(0,u["start"]),min(span,u["end"])) if 0<=v<=span]))
    vs, ms = [], []
    for x in xs:
        v = left - sum(p["magnitude"] for p in points if p["position"] < x)
        m = left*x - sum(p["magnitude"]*max(0,x-p["position"]) for p in points)
        for u in uniforms:
            a,b=max(0,u["start"]),min(span,u["end"])
            length=max(0,min(x,b)-a)
            if length:
                v -= u["magnitude"]*length
                m -= u["magnitude"]*length*(x-(a+min(x,b))/2)
        if support == "Cantilever":
            # For a cantilever use the loads to the right of the cut.
            v = sum(p["magnitude"] for p in points if p["position"] >= x)
            m = sum(p["magnitude"]*(p["position"]-x) for p in points if p["position"] >= x)
            for u in uniforms:
                a,b=max(x,max(0,u["start"])),min(span,u["end"])
                if b>a:
                    v += u["magnitude"]*(b-a)
                    m += u["magnitude"]*(b-a)*(b-a)/2
        vs.append(v); ms.append(m)
    idx=max(range(len(xs)), key=lambda i:abs(ms[i]))
    max_m=abs(ms[idx]); max_v=max(map(abs,vs))
    sec=section or state["section"]
    ix,sx,_=SECTIONS[state["material"]][sec]
    # Integrate y''=M/EI on inches. Remove the residual end displacement for
    # the simply-supported boundary condition.
    slopes=[0.0]; ys=[0.0]
    for i in range(1,len(xs)):
        dx=(xs[i]-xs[i-1])*12
        c0=ms[i-1]*12/(E_MOD[state["material"]]*ix)
        c1=ms[i]*12/(E_MOD[state["material"]]*ix)
        slopes.append(slopes[-1]+(c0+c1)*dx/2)
        ys.append(ys[-1]+(slopes[-2]+slopes[-1])*dx/2)
    if support == "Simply supported":
        end=ys[-1]
        ys=[y-end*x/span for x,y in zip(xs,ys)]
    else:
        ys=[-y for y in ys]
    di=max(range(len(ys)),key=lambda i:abs(ys[i]))
    y_max=abs(ys[di]); allow=span*12/(240 if state["limit"]=="L/240" else 360)
    stress=max_m*12/sx
    return dict(xs=xs,vs=vs,ms=ms,ys=ys,left=left,right=right,max_v=max_v,
                max_m=max_m,mx=xs[idx],y_max=y_max,yx=xs[di],allow=allow,
                stress=stress,bend_ratio=stress/FB[state["material"]],defl_ratio=y_max/allow)


class BeamDesigner(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Beam Designer")
        self.geometry("1320x900"); self.minsize(950,680); self.configure(bg=BG)
        self.state = dict(name="Untitled beam",support="Simply supported",span=20.0,
                          points=[],uniforms=[dict(magnitude=1.0,start=0.0,end=20.0)],
                          material="Steel",section="W12x26",limit="L/360",waste=15)
        self.design_file=Path.home()/".beam_designer_designs.json"
        self.status=tk.StringVar(value="Ready")
        self._make_ui(); self.refresh()

    def _make_ui(self):
        menubar=tk.Menu(self)
        file_menu=tk.Menu(menubar,tearoff=False)
        file_menu.add_command(label="Save…",command=self.save_file,accelerator="Ctrl+S")
        file_menu.add_command(label="Open…",command=self.open_file,accelerator="Ctrl+O")
        menubar.add_cascade(label="File",menu=file_menu)
        self.configure(menu=menubar)
        self.bind_all("<Control-s>",lambda event:self.save_file())
        self.bind_all("<Control-o>",lambda event:self.open_file())
        top=ttk.Frame(self,padding=(16,10)); top.pack(fill="x")
        ttk.Label(top,text="▰  BEAM DESIGNER",font=("TkDefaultFont",16,"bold"),foreground=NAVY).pack(side="left")
        for label,cmd in (("Export results",self.export_results),("Report",self.report)):
            ttk.Button(top,text=label,command=cmd).pack(side="right",padx=3)
        body=ttk.Frame(self); body.pack(fill="both",expand=True)
        self.sidebar=ttk.Frame(body,width=330,padding=14); self.sidebar.pack(side="left",fill="y"); self.sidebar.pack_propagate(False)
        self.main=ttk.Frame(body,padding=(5,8,16,14)); self.main.pack(side="left",fill="both",expand=True)
        def field(label, var, values=None):
            ttk.Label(self.sidebar,text=label).pack(anchor="w",pady=(7,2))
            w=ttk.Combobox(self.sidebar,textvariable=var,values=values,state="readonly") if values else ttk.Entry(self.sidebar,textvariable=var)
            w.pack(fill="x"); w.bind("<<ComboboxSelected>>",lambda e:self.refresh()); return w
        ttk.Label(self.sidebar,text="DESIGN INPUTS",font=("TkDefaultFont",11,"bold"),foreground=NAVY).pack(anchor="w")
        self.name=tk.StringVar(value=self.state["name"]); field("Design name",self.name)
        self.support=tk.StringVar(value=self.state["support"]); field("Support",self.support,["Simply supported","Cantilever"])
        ttk.Label(self.sidebar,text="Span · ft").pack(anchor="w",pady=(7,2))
        row=ttk.Frame(self.sidebar);row.pack(fill="x")
        self.span=tk.DoubleVar(value=20); ttk.Scale(row,from_=4,to=40,variable=self.span,command=lambda _:self.refresh()).pack(side="left",fill="x",expand=True)
        ttk.Spinbox(row,from_=4,to=40,increment=.25,textvariable=self.span,width=6,command=self.refresh).pack(side="right")
        self.material=tk.StringVar(value="Steel"); field("Material",self.material,list(SECTIONS))
        self.section=tk.StringVar(value="W12x26"); self.section_box=field("Section",self.section,list(SECTIONS["Steel"]))
        ttk.Label(self.sidebar,text="Deflection limit").pack(anchor="w",pady=(7,2))
        self.limit=tk.StringVar(value="L/360")
        for v in ("L/240","L/360"):
            ttk.Radiobutton(self.sidebar,text=v,variable=self.limit,value=v,command=self.refresh).pack(anchor="w")
        ttk.Label(self.sidebar,text="Waste factor · not used in checks").pack(anchor="w",pady=(7,2))
        self.waste=tk.IntVar(value=15); ttk.Scale(self.sidebar,from_=0,to=15,variable=self.waste,command=lambda _:self.waste_label.configure(text=f"{int(self.waste.get())}%")).pack(fill="x")
        self.waste_label=ttk.Label(self.sidebar,text="15%");self.waste_label.pack(anchor="e")
        ttk.Separator(self.sidebar).pack(fill="x",pady=9)
        ttk.Label(self.sidebar,text="LOADS",font=("TkDefaultFont",11,"bold"),foreground=NAVY).pack(anchor="w")
        self.loads=ttk.Frame(self.sidebar);self.loads.pack(fill="x")
        self.point_vars=[];self.uniform_vars=[]
        ttk.Label(self.sidebar,text="Saved designs").pack(anchor="w",pady=(7,2))
        self.saved_name=tk.StringVar()
        self.saved_box=ttk.Combobox(self.sidebar,textvariable=self.saved_name,state="readonly")
        self.saved_box.pack(fill="x");self.saved_box.bind("<<ComboboxSelected>>",self.load_saved)
        buttons=ttk.Frame(self.sidebar);buttons.pack(fill="x",pady=5)
        ttk.Button(buttons,text="＋ Point load",command=self.add_point).pack(side="left",expand=True,fill="x")
        ttk.Button(buttons,text="＋ Uniform load",command=self.add_uniform).pack(side="left",expand=True,fill="x")
        self.statusbar=ttk.Label(self,textvariable=self.status,anchor="w",padding=(12,5));self.statusbar.pack(side="bottom",fill="x")
        self.heading=ttk.Label(self.main,text="BEAM RESPONSE",font=("TkDefaultFont",11,"bold"),foreground=NAVY);self.heading.pack(anchor="w")
        self.canvas=tk.Canvas(self.main,bg="white",highlightthickness=1,highlightbackground="#e1e8f0",height=500)
        self.canvas.pack(fill="both",expand=True,pady=8);self.canvas.bind("<Configure>",lambda e:self.draw())
        self.summary=ttk.Label(self.main,text="",font=("TkDefaultFont",11));self.summary.pack(anchor="w",pady=4)
        self.recommend=ttk.Label(self.main,text="",font=("TkDefaultFont",11,"bold"));self.recommend.pack(anchor="w")
        self.section_box.bind("<<ComboboxSelected>>",lambda e:self.refresh())
        self.material.trace_add("write",self.material_changed)
        self.support.trace_add("write",lambda *_:self.refresh())

    def material_changed(self,*_):
        choices=list(SECTIONS[self.material.get()]); self.section_box.configure(values=choices)
        self.section.set("W12x26" if self.material.get()=="Steel" else "2x8"); self.refresh()

    def collect(self):
        s=float(self.span.get()); s=max(4,min(40,s)); self.span.set(s)
        self.state.update(name=self.name.get().strip() or "Untitled beam",support=self.support.get(),span=s,
            material=self.material.get(),section=self.section.get(),limit=self.limit.get(),waste=int(self.waste.get()))
        self.state["points"]=[dict(magnitude=float(x[0].get()),position=float(x[1].get())) for x in self.point_vars]
        self.state["uniforms"]=[dict(magnitude=float(x[0].get()),start=float(x[1].get()),end=float(x[2].get())) for x in self.uniform_vars]
        return self.state

    def rebuild_loads(self):
        for child in self.loads.winfo_children(): child.destroy()
        self.point_vars=[]; self.uniform_vars=[]
        for kind, items, target in (("Point",self.state["points"],self.point_vars),("Uniform",self.state["uniforms"],self.uniform_vars)):
            for i,item in enumerate(items):
                line=ttk.Frame(self.loads);line.pack(fill="x",pady=3)
                ttk.Label(line,text=f"{kind} {i+1}").pack(anchor="w")
                vars=[]
                keys=("magnitude","position") if kind=="Point" else ("magnitude","start","end")
                labels=("kips","ft") if kind=="Point" else ("k/ft","start ft","end ft")
                for key,label in zip(keys,labels):
                    v=tk.DoubleVar(value=item[key]);vars.append(v)
                    e=ttk.Entry(line,textvariable=v,width=7);e.pack(side="left",padx=1)
                    e.bind("<FocusOut>",lambda event:self.refresh())
                target.append(vars)
                ttk.Button(line,text="×",width=2,command=lambda k=kind,j=i:self.remove_load(k,j)).pack(side="right")

    def refresh(self):
        if not hasattr(self,"loads"):return
        try:
            if hasattr(self,"point_vars") and (self.point_vars or self.uniform_vars):
                # Preserve edits before rebuilding load controls.
                self.state["points"]=[dict(magnitude=max(0,min(100,v[0].get())),position=max(0,min(float(self.span.get()),round(v[1].get()*4)/4))) for v in self.point_vars]
                self.state["uniforms"]=[dict(magnitude=max(0,min(10,v[0].get())),start=max(0,min(float(self.span.get()),round(v[1].get()*4)/4)),end=max(0,min(float(self.span.get()),round(v[2].get()*4)/4))) for v in self.uniform_vars]
            self.collect(); self.rebuild_loads(); self.result=analyze(self.state)
            self.summary.configure(text=f"Reactions  {self.result['left']:.2f} k / {self.result['right']:.2f} k     |     Max shear  {self.result['max_v']:.2f} k     |     Max moment  {self.result['max_m']:.2f} kip-ft at {self.result['mx']:.2f} ft     |     Deflection  {self.result['y_max']:.3f} in at {self.result['yx']:.2f} ft")
            self.draw()
            self.recommend.configure(text=f"Bending: {self.result['stress']:.2f}/{FB[self.state['material']]:g} ksi {'PASS' if self.result['bend_ratio']<=1 else 'FAIL'}  ·  Deflection: {self.result['y_max']:.3f}/{self.result['allow']:.3f} in {'PASS' if self.result['defl_ratio']<=1 else 'FAIL'}  ·  {self.suggestion()}")
        except (ValueError,tk.TclError,KeyError) as exc:
            self.status.set(f"Check input values: {exc}")

    def suggestion(self):
        passing=[]
        for sec,(ix,sx,weight) in SECTIONS[self.state["material"]].items():
            r=analyze(self.state,sec)
            if r["bend_ratio"]<=1 and r["defl_ratio"]<=1:passing.append((weight,-ix,sec))
        if not passing:return "No passing section"
        sec=min(passing)[2]
        return f"Lightest passing section: {sec}  ·  Use section"

    def add_point(self):
        self.state["points"].append(dict(magnitude=1,position=round(float(self.span.get())/2*4)/4));self.rebuild_loads();self.refresh()
    def add_uniform(self):
        self.state["uniforms"].append(dict(magnitude=1,start=0,end=float(self.span.get())));self.rebuild_loads();self.refresh()
    def remove_load(self,kind,index):
        self.state["points" if kind=="Point" else "uniforms"].pop(index);self.rebuild_loads();self.refresh()

    def draw(self):
        if not hasattr(self,"result"):return
        c=self.canvas;c.delete("all");w=max(500,c.winfo_width());span=self.state["span"];x0=70;x1=w-35;xf=lambda x:x0+x/span*(x1-x0)
        c.create_text(20,20,anchor="w",text=self.state["name"],fill=NAVY,font=("TkDefaultFont",12,"bold"))
        beam_y=80;c.create_line(x0,beam_y,x1,beam_y,width=5,fill=NAVY)
        for x in (x0,x1): c.create_polygon(x,beam_y+2,x-11,beam_y+20,x+11,beam_y+20,fill="#bfdbfe",outline=BLUE)
        if self.state["support"]=="Cantilever":c.create_rectangle(x0-14,beam_y-16,x0-7,beam_y+25,fill=NAVY)
        for u in self.state["uniforms"]:
            a,b=max(0,u["start"]),min(span,u["end"])
            if b<=a:continue
            for x in range(int(xf(a)),int(xf(b))+1, max(14,int((x1-x0)/35))):
                c.create_line(x,beam_y-28,x,beam_y-4,fill=BLUE,arrow="last",width=2)
            c.create_line(xf(a),beam_y-30,xf(b),beam_y-30,fill=BLUE,width=2)
        for i,p in enumerate(self.state["points"]):
            px=xf(p["position"]);c.create_line(px,beam_y-36,px,beam_y-4,fill="#dc2626",arrow="last",width=2,tags=(f"pt{i}","point"))
            c.create_text(px,beam_y-44,text=f"{p['magnitude']:g} k",fill="#b91c1c",tags=(f"pt{i}","point"))
        colors=(BLUE,"#16a34a","#d97706"); names=("SHEAR · kips","MOMENT · kip-ft","DEFLECTION · in"); arrays=(self.result["vs"],self.result["ms"],self.result["ys"]); top=135; height=max(90,(c.winfo_height()-190)//3)
        for j,(name,vals,color) in enumerate(zip(names,arrays,colors)):
            y0=top+j*height;cy=y0+height/2;c.create_text(18,y0+8,anchor="nw",text=name,fill=NAVY,font=("TkDefaultFont",9,"bold"));c.create_line(x0,cy,x1,cy,fill="#dbe3ed")
            peak=max(max(map(abs,vals)),.001);scale=(height*.35)/peak
            coords=[(xf(x),cy-v*scale) for x,v in zip(self.result["xs"],vals)]
            flat=[q for pair in coords for q in pair]
            if len(flat)>4:
                c.create_polygon([x0,cy]+flat+[x1,cy],fill=color,stipple="gray25",outline="")
                c.create_line(*flat,fill=color,width=2)
            k=max(range(len(vals)),key=lambda i:abs(vals[i]));px,py=coords[k]
            c.create_text(px,py-11,text=f"{abs(vals[k]):.3f} at {self.result['xs'][k]:.2f} ft",fill=color,font=("TkDefaultFont",9,"bold"))
        self.canvas.tag_bind("point","<ButtonPress-1>",self.drag_start)
        self.canvas.tag_bind("point","<B1-Motion>",self.drag_move)
        c.bind("<Motion>",self.hover)

    def drag_start(self,event):self.drag_index=next((i for i in range(len(self.state["points"])) if f"pt{i}" in self.canvas.gettags("current")),None)
    def drag_move(self,event):
        if getattr(self,"drag_index",None) is None:return
        x0=70;x1=self.canvas.winfo_width()-35
        self.state["points"][self.drag_index]["position"]=max(0,min(self.state["span"],round((event.x-x0)/(x1-x0)*self.state["span"]*4)/4));self.rebuild_loads();self.refresh()
    def hover(self,event):
        if not hasattr(self,"result"):return
        x0=70;x1=self.canvas.winfo_width()-35;x=max(0,min(self.state["span"],(event.x-x0)/(x1-x0)*self.state["span"]))
        i=min(range(len(self.result["xs"])),key=lambda j:abs(self.result["xs"][j]-x))
        self.status.set(f"x {x:.2f} ft  ·  V {self.result['vs'][i]:.2f} k  ·  M {self.result['ms'][i]:.2f} kip-ft  ·  y {self.result['ys'][i]:.3f} in")

    def save_design(self):
        state=self.collect();designs={}
        try:designs=json.loads(self.design_file.read_text())
        except (OSError,json.JSONDecodeError):pass
        designs[state["name"]]=state
        try:
            self.design_file.write_text(json.dumps(designs,indent=2));self.saved_box.configure(values=list(designs));self.saved_name.set(state["name"]);self.status.set(f"Saved {state['name']}")
        except OSError as e:messagebox.showerror("Save failed",str(e))
    def save_file(self):
        path=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("Beam design","*.json")],title="Save beam")
        if not path:return
        try:
            Path(path).write_text(json.dumps(self.collect(),indent=2))
            self.status.set(f"Saved beam to {Path(path).name}")
        except OSError as e:messagebox.showerror("Save failed",str(e))
    def open_file(self):
        path=filedialog.askopenfilename(filetypes=[("Beam design","*.json")],title="Open beam")
        if not path:return
        try:
            data=json.loads(Path(path).read_text())
            material=data.get("material","Steel")
            if material not in SECTIONS:raise ValueError("Unknown material")
            support=data.get("support","Simply supported")
            if support not in ("Simply supported","Cantilever"):raise ValueError("Unknown support type")
            data["span"]=max(4,min(40,float(data.get("span",20))))
            data["points"]=[dict(magnitude=max(0,min(100,float(p["magnitude"]))),position=max(0,min(data["span"],round(float(p["position"])*4)/4))) for p in data.get("points",[])]
            data["uniforms"]=[dict(magnitude=max(0,min(10,float(u["magnitude"]))),start=max(0,min(data["span"],round(float(u["start"])*4)/4)),end=max(0,min(data["span"],round(float(u["end"])*4)/4))) for u in data.get("uniforms",[])]
            data["section"]=data.get("section","W12x26" if material=="Steel" else "2x8")
            if data["section"] not in SECTIONS[material]:raise ValueError("Section does not match the selected material")
            self.state.update(data)
            self.name.set(data.get("name","Untitled beam"));self.span.set(data["span"]);self.support.set(support)
            self.material.set(material);self.section_box.configure(values=list(SECTIONS[material]));self.section.set(data["section"])
            self.limit.set(data.get("limit","L/360"));self.waste.set(data.get("waste",15))
            self.rebuild_loads();self.refresh();self.status.set(f"Opened beam from {Path(path).name}")
        except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as e:
            messagebox.showerror("Could not open beam",str(e))
    def load_saved(self,event=None):
        try:
            data=json.loads(self.design_file.read_text())[self.saved_name.get()]
            self.state.update(data);self.name.set(data.get("name","Untitled beam"));self.span.set(data.get("span",20))
            self.support.set(data.get("support","Simply supported"));self.material.set(data.get("material","Steel"))
            self.section_box.configure(values=list(SECTIONS[self.material.get()]));self.section.set(data.get("section","W12x26"))
            self.limit.set(data.get("limit","L/360"));self.waste.set(data.get("waste",15));self.rebuild_loads();self.refresh();self.status.set("Design loaded")
        except (OSError,ValueError,KeyError) as e:messagebox.showerror("Load failed",str(e))
    def export_design(self):
        path=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("Beam design","*.json")])
        if path:
            Path(path).write_text(json.dumps(self.collect(),indent=2));self.status.set("Design exported")
    def import_design(self):
        path=filedialog.askopenfilename(filetypes=[("Beam design","*.json")])
        if path:
            try:
                data=json.loads(Path(path).read_text());self.state.update(data)
                self.name.set(data.get("name","Untitled beam"));self.span.set(data.get("span",20));self.support.set(data.get("support","Simply supported"));self.material.set(data.get("material","Steel"));self.section_box.configure(values=list(SECTIONS[self.material.get()]));self.section.set(data.get("section","W12x26"));self.limit.set(data.get("limit","L/360"));self.waste.set(data.get("waste",15));self.rebuild_loads();self.refresh();self.status.set("Design imported")
            except (ValueError,KeyError,OSError) as e:messagebox.showerror("Invalid design",str(e))
    def report(self):
        r=self.result;s=self.state
        text=(f"Beam Designer — {s['name']}\n\nSupport: {s['support']}\nSpan: {s['span']} ft\nMaterial / section: {s['material']} / {s['section']}\n"
              f"Reactions: {r['left']:.3f} k / {r['right']:.3f} k\nMaximum shear: {r['max_v']:.3f} k\nMaximum moment: {r['max_m']:.3f} kip-ft at {r['mx']:.3f} ft\n"
              f"Maximum deflection: {r['y_max']:.4f} in at {r['yx']:.3f} ft (limit {r['allow']:.4f} in)\nBending stress: {r['stress']:.3f} ksi / {FB[s['material']]:g} ksi\nRecommendation: {self.suggestion()}\n")
        path=filedialog.asksaveasfilename(defaultextension=".txt",filetypes=[("Text report","*.txt")])
        if path:Path(path).write_text(text);self.status.set("Report exported")

    def export_results(self):
        path=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV for Excel","*.csv")],title="Export beam results")
        if not path:return
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as output:
                writer=csv.writer(output)
                writer.writerow(["x (ft)","V (kips)","M (kip-ft)","Deflection (in)"])
                writer.writerows((f"{x:.6f}",f"{v:.6f}",f"{m:.6f}",f"{y:.6f}")
                                 for x,v,m,y in zip(self.result["xs"],self.result["vs"],self.result["ms"],self.result["ys"]))
            self.status.set(f"Results exported to {Path(path).name}")
        except OSError as e:messagebox.showerror("Export failed",str(e))


if __name__ == "__main__":
    BeamDesigner().mainloop()
