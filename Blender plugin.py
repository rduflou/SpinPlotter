bl_info = {
    "name": "Spin Plot",
    "location": "3D View",
    "category": "Object",
}

import bpy
import math
import os
import glob

from bpy.props import (StringProperty,
                       BoolProperty,
                       IntProperty,
                       FloatProperty,
                       EnumProperty,
                       PointerProperty,
                       )
from bpy.types import (Panel,
                       Operator,
                       PropertyGroup,
                       )
                       
listOfSpins = []
currentSpin = None
listOfArrows = []
currentArrow = None
arrowForSpinSets = None
settings = None
adjustmentMode = True

#############################
#                           #
#          CLASSES          #
#                           #
#############################
                       
class Spin:
    
    def __init__(self, temp_name = "Spin"):
        self.times = [0]
        self.locations = [[0, 0, 0]]
        self.vectors = [[0, 0, 1]]
        self.object = None
        self.shaft = None
        self.tip = None
        
        self.times_eq_bool = True
        self.locations_eq_bool = True
        self.vectors_eq_bool = True
        
        self.t_sta_eq = 0.0
        self.t_end_eq = 1.0
        self.t_ste_eq = 1
        self.x_eq = "0"
        self.y_eq = "0"
        self.z_eq = "0"
        self.vx_eq = ""
        self.vy_eq = ""
        self.vz_eq = ""
        self.n_eq = ""
        
        self.file_path = ""
        self.t_sta_file = ""
        self.t_end_file = ""
        self.x_file = ""
        self.y_file = ""
        self.z_file = ""
                
        self.linkedArrow = None
        
        passed = False
        index = 1
        while not passed:
            passed = True
            for s in listOfSpins:
                if temp_name == s.name:
                    passed = False
            if passed:
                self.name = temp_name
            else:
                temp_name = temp_name[0:4] + str(index)
                index += 1
    
    def Create(self,scene):
        if self.linkedArrow != None:
            self.object = self.linkedArrow.object.copy()
            self.shaft = self.linkedArrow.shaft.copy()
            self.tip = self.linkedArrow.tip.copy()
            self.shaft.parent = self.object
            self.tip.parent = self.object
            scene.objects.link(self.object)
            scene.objects.link(self.shaft)
            scene.objects.link(self.tip)
            
            self.shaft.hide = False
            self.shaft.hide_render = False
            self.tip.hide = False
            self.tip.hide_render = False
            
    def UseEquations(self):
        if self.times_eq_bool:
            times = []
            if self.t_end_eq > self.t_sta_eq and self.t_ste_eq > 0:    
                for i in range(0,self.t_ste_eq+1):
                    times.append(self.t_sta_eq + (self.t_end_eq - self.t_sta_eq)*i/self.t_ste_eq)
            else:
                times.append(self.t_sta_eq)
        else:
            times = self.times
        values = []
        equations = [self.x_eq, self.y_eq, self.z_eq, self.vx_eq, self.vy_eq, self.vz_eq, self.n_eq]
        failed = False
        if self.locations_eq_bool:
            for eq in equations[0:3]:
                v = EvaluateEquation(eq,times)
                if v == "FAILED!":
                    print("FAILED! UseEquations 1")
                    failed = True
                else:
                    values.append(v)
        if self.vectors_eq_bool:
            numberOfBlanks = 0
            for eq in equations[3:7]:
                if eq == "":
                    numberOfBlanks += 1
            if numberOfBlanks > 1:
                print("FAILED! UseEquations 2")
                failed = True
            elif numberOfBlanks == 0:
                norms = EvaluateEquation(equations[6],times)
                if norms == "FAILED!":
                    print("FAILED! UseEquations 3")
                    failed = True
                else:
                    tempValues = []
                    for eq in equations[3:6]:
                        v = EvaluateEquation(eq,times)
                        if v == "FAILED!":
                            print("FAILED! UseEquations 4")
                            failed = True
                        else:
                            tempValues.append(v)
                    for tv in tempValues:
                        values.append([])
                        for i in range(0,len(tv)):
                            norm = tempValues[0][i]**2 + tempValues[1][i]**2 + tempValues[2][i]**2
                            values[-1].append(tv[i]*norms[i]/norm)
            else:
                if self.vx_eq == "":
                    v1 = EvaluateEquation(self.vy_eq,times)
                    v2 = EvaluateEquation(self.vz_eq,times)
                    norms = EvaluateEquation(self.n,times)
                    if v1 == "FAILED!" or v2 == "FAILED!" or norms == "FAILED!":
                        print("FAILED! UseEquations 5")
                        failed = True
                    else:
                        v = []
                        for i in range(0,len(times)):
                            v.append(math.sqrt(norms[i]**2 - v1[i]**2 - v2[i]**2))
                        values = values + [v,v1,v2]
                elif self.vy_eq == "":
                    v1 = EvaluateEquation(self.vx_eq,times)
                    v2 = EvaluateEquation(self.vz_eq,times)
                    norms = EvaluateEquation(self.n,times)
                    if v1 == "FAILED!" or v2 == "FAILED!" or norms == "FAILED!":
                        print("FAILED! UseEquations 6")
                        failed = True
                    else:
                        v = []
                        for i in range(0,len(times)):
                            v.append(math.sqrt(norms[i]**2 - v1[i]**2 - v2[i]**2))
                        values = values + [v1,v,v2]
                elif self.vz_eq == "":
                    v1 = EvaluateEquation(self.vx_eq,times)
                    v2 = EvaluateEquation(self.vy_eq,times)
                    norms = EvaluateEquation(self.n,times)
                    if v1 == "FAILED!" or v2 == "FAILED!" or norms == "FAILED!":
                        print("FAILED! UseEquations 7")
                        failed = True
                    else:
                        v = []
                        for i in range(0,len(times)):
                            if norms[i]**2 - v1[i]**2 - v2[i]**2 < 0:
                                v.append(0.0)
                            else:
                                v.append(math.sqrt(norms[i]**2 - v1[i]**2 - v2[i]**2))
                        values = values + [v1,v2,v]
                else:
                    v1 = EvaluateEquation(self.vx_eq,times)
                    v2 = EvaluateEquation(self.vy_eq,times)
                    v3 = EvaluateEquation(self.vz_eq,times)
                    if v1 == "FAILED!" or v2 == "FAILED!" or v3 == "FAILED!":
                        print("FAILED! UseEquations 8")
                        failed = True
                    else:
                        values = values + [v1,v2,v3]
        if not failed:
            self.times = times
            if self.locations_eq_bool:
                self.locations = []
            if self.vectors_eq_bool:
                self.vectors = []
            for i in range(0,len(times)):
                if self.locations_eq_bool:
                    self.locations.append([values[0][i],values[1][i],values[2][i]])
                elif i >= len(self.locations):
                    self.locations.append(self.locations[-1])
                if self.vectors_eq_bool:
                    self.vectors.append([values[3][i],values[4][i],values[5][i]])
                elif i >= len(self.vectors):
                    self.vectors.append(self.vectors[-1])
        else:
            return "FAILED!"
        
    def Delete(self,scene):
        if self.object != None:
            bpy.ops.object.select_all(action='DESELECT')
            self.object.select = True
            self.shaft.select = True
            self.tip.select = True
            scene.objects.unlink(self.object)
            
            self.object = None
            self.shaft = None
            self.tip = None
            bpy.ops.object.delete()
        
class Arrow:
    
    def __init__(self):
        temp_name = "Arrow"
        passed = False
        index = 1
        while not passed:
            passed = True
            for a in listOfArrows:
                if temp_name == a.name:
                    passed = False
            if passed:
                self.name = temp_name
            else:
                temp_name = temp_name[0:5] + str(index)
                index += 1
        bpy.ops.object.add(type='EMPTY',location=(0,0,0))
        bpy.ops.mesh.primitive_cylinder_add(radius=0.5,location=(0,0,0))
        bpy.ops.mesh.primitive_cone_add(depth=1,radius1=0.75,location=(0,0,1.5))
        objects = bpy.data.objects
        self.object = objects["Empty"]
        self.shaft = objects["Cylinder"]
        self.shaft.parent = self.object
        self.tip = objects["Cone"]
        self.tip.parent = self.object
        self.object.name = self.name
        self.shaft.name = self.name + "_cylinder"
        self.tip.name = self.name + "_cone"
        self.object.hide_render = True
        self.shaft.hide_render = True
        self.tip.hide_render = True
        
    def Delete(self):
        for s in listOfSpins:
            if s.linkedArrow == self:
                s.linkedArrow = None        
        bpy.ops.object.select_all(action='DESELECT')
        self.object.select = True
        self.shaft.select = True
        self.tip.select = True
        bpy.ops.object.delete()
        
    def SetName(self,name):
        self.name = name
        self.object.name = name
        self.shaft.name = name + "_cylinder"
        self.tip.name = name + "_cone"
        
    def Select(self):
        self.object.hide = False
        self.shaft.hide = False
        self.tip.hide = False
    
    def Deselect(self):
        self.object.hide = True
        self.object.select = False
        self.shaft.hide = True
        self.shaft.select = False
        self.tip.hide = True
        self.tip.select = False
                       
class SpinPlotSettings(PropertyGroup):

    resetOnCreate = BoolProperty(
        name = "Reset on creating scene",
        description = "Resets the scene and deletes all objects before creating spins.",
        default = False
        )
        
    currentSpinName = StringProperty(
        name="Name",
        description="Name of the current selected spin.",
        default="",
        maxlen=1024,
        )
        
    currentSpinLinkedArrow = StringProperty(
        name="Linked Arrow",
        description="The arrow the current spin is linked to, if any.",
        default="",
        maxlen=1024,
        )
        
    currentSpinFilePath = StringProperty(
        name="Path",
        description="Path to the file to load in.",
        subtype="FILE_PATH",
        default = "")
        
    spinSetFilePath = StringProperty(
        name="Path",
        description="Path to the file to load in.",
        subtype="FILE_PATH",
        default = "")
        
    currentArrowName = StringProperty(
        name="Name",
        description="Name of the current selected arrow.",
        default="",
        maxlen=1024,
        )
        
    startingTime = FloatProperty(
        name = "Starting time",
        description = "The time t corresponding to the first frame.",
        default = 0.0,
        )

    endingTime = FloatProperty(
        name = "Ending time",
        description = "The time t corresponding to the final frame",
        default = 1.0,
        )

#    my_int = IntProperty(
#        name = "Int Value",
#        description="A integer property",
#        default = 23,
#        min = 10,
#        max = 100
#        )
#
#    my_float = FloatProperty(
#        name = "Float Value",
#        description = "A float property",
#        default = 23.7,
#        min = 0.01,
#        max = 30.0
#        )
#
#    my_string = StringProperty(
#        name="User Input",
#        description=":",
#        default="",
#        maxlen=1024,
#        )
#
#    my_enum = EnumProperty(
#        name="Dropdown:",
#        description="Apply Data to attribute.",
#        items=[ ('OP1', "Option 1", ""),
#                ('OP2', "Option 2", ""),
#                ('OP3', "Option 3", ""),
#               ]
#        )

#############################
#                           #
#       OPERATORS           #
#                           #
#############################

class CreateScene(bpy.types.Operator):
    bl_idname = "scene.create"
    bl_label = "Create Scene"
    bl_description = "Creation of objects to be rendered."

    def invoke(self, context, event):
        settings = context.scene.spinplotsettings
        global adjustmentMode
        if adjustmentMode:
            adjustmentMode = False
            if settings.resetOnCreate:
                objects = bpy.data.objects
                bpy.ops.object.select_all(action='SELECT')
                objects["Camera"].select = False
                objects["Camera"].location = (0, -10.0, 10.0)
                objects["Camera"].rotation_euler = (math.pi/4, 0, 0)
                objects["Lamp"].select = False
            for a in listOfArrows:
                a.Deselect()
            if settings.resetOnCreate:
                bpy.ops.object.delete()
            
            for s in listOfSpins:
                s.Create(context.scene)
        return {'FINISHED'}
    
class AdjustScene(bpy.types.Operator):
    bl_idname = "scene.adjust"
    bl_label = "Adjust Scene"
    bl_description = "Go back to adjusting mode"

    def invoke(self, context, event):
        global adjustmentMode
        if not adjustmentMode:
            adjustmentMode = True
            if currentArrow != None:
                currentArrow.Select()
                for s in listOfSpins:
                    s.Delete(context.scene)
        return {'FINISHED'}
        
class AddSpin(bpy.types.Operator):
    bl_idname = "spin.add"
    bl_label = "Add Spin"
    bl_description = "Add a spin."

    def invoke(self, context, event):
        if adjustmentMode:
            spin = Spin()
            listOfSpins.append(spin)
            SetCurrentSpin(settings=context.scene.spinplotsettings,spin=spin)
        return {'FINISHED'}

class SelectSpin(bpy.types.Operator):
    bl_idname = "spin.select"
    bl_label = "Select Spin"
    bl_description = "Select a spin."
    bl_options = {'REGISTER', 'UNDO'}
    name = StringProperty()

    def execute(self, context):
        if adjustmentMode:
            global currentSpin
            for s in listOfSpins:
                if s.name == self.name:
                    SetCurrentSpin(settings=context.scene.spinplotsettings,spin=s)
        return {'FINISHED'}
    
class DeleteSpin(bpy.types.Operator):
    bl_idname = "spin.delete"
    bl_label = "Delete Spin"
    bl_description = "Delete the currently selected spin."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if adjustmentMode:
            global currentSpin
            if currentSpin != None:
                #currentSpin.Delete(context.scene)
                listOfSpins.remove(currentSpin)
                if len(listOfSpins) != 0:
                    SetCurrentSpin(settings=context.scene.spinplotsettings,spin=listOfSpins[0])
                else:
                    SetCurrentSpin(settings=context.scene.spinplotsettings,spin=None)
        return {'FINISHED'}
    
class ViewSpin(bpy.types.Operator):
    bl_idname = "spin.view"
    bl_label = "View values"
    bl_description = "View the vectors and locations allocated to this spin."
    
    def invoke(self, context, event):
        if adjustmentMode:
            return context.window_manager.invoke_popup(self,width=500)
        else:
            return {'FINISHED'}

    def execute(self, context):
        return {'FINISHED'}
    
    def draw(self, context):
        row = self.layout.row()
        row.label("Time:")
        row.label("x location:")
        row.label("y location:")
        row.label("z location:")
        row.label("x vector:")
        row.label("y vector:")
        row.label("z vector:")
        for i in range(0,len(currentSpin.times)):
            row = self.layout.row()
            row.label(str(currentSpin.times[i]))
            row.label(str(currentSpin.locations[i][0]))
            row.label(str(currentSpin.locations[i][1]))
            row.label(str(currentSpin.locations[i][2]))
            row.label(str(currentSpin.vectors[i][0]))
            row.label(str(currentSpin.vectors[i][1]))
            row.label(str(currentSpin.vectors[i][2]))
        
    
class CreateSpin(bpy.types.Operator):
    bl_idname = "spin.create"
    bl_label = "Equations"
    bl_description = "Create vectors and locations through equations."
    bl_options = {'REGISTER', 'UNDO'}
    
    start = bpy.props.FloatProperty()
    end = bpy.props.FloatProperty()
    steps = bpy.props.IntProperty()
    
    times_bool = bpy.props.BoolProperty(name = "Use equations for the times.")
    locations_bool = bpy.props.BoolProperty(name = "Use equations for the locations.")
    vectors_bool = bpy.props.BoolProperty(name = "Use equations for the vectors.")
    
    x = bpy.props.StringProperty()
    y = bpy.props.StringProperty()
    z = bpy.props.StringProperty()
    vx = bpy.props.StringProperty()
    vy = bpy.props.StringProperty()
    vz = bpy.props.StringProperty()
    n = bpy.props.StringProperty()
    
    def invoke(self, context, event):
        if adjustmentMode and currentSpin != None:
            self.times_bool = currentSpin.times_eq_bool
            self.locations_bool = currentSpin.locations_eq_bool
            self.vectors_bool = currentSpin.vectors_eq_bool
            self.start = currentSpin.t_sta_eq
            self.end = currentSpin.t_end_eq
            self.steps = currentSpin.t_ste_eq
            self.x = currentSpin.x_eq
            self.y = currentSpin.y_eq
            self.z = currentSpin.z_eq
            self.vx = currentSpin.vx_eq
            self.vy = currentSpin.vy_eq
            self.vz = currentSpin.vz_eq
            self.n = currentSpin.n_eq
            return context.window_manager.invoke_props_dialog(self,width=500)
        else:
            return {'FINISHED'}

    def execute(self, context):
        if adjustmentMode:
            currentSpin.times_eq_bool = self.times_bool
            currentSpin.locations_eq_bool = self.locations_bool
            currentSpin.vectors_eq_bool = self.vectors_bool
            currentSpin.t_sta_eq = self.start
            currentSpin.t_end_eq = self.end
            currentSpin.t_ste_eq = self.steps
            currentSpin.x_eq = self.x
            currentSpin.y_eq = self.y
            currentSpin.z_eq = self.z
            currentSpin.vx_eq = self.vx
            currentSpin.vy_eq = self.vy
            currentSpin.vz_eq = self.vz
            currentSpin.n_eq = self.n
            currentSpin.UseEquations()
        return {'FINISHED'}

    def draw(self, context):
        row = self.layout.row()
        row.label("Times:")
        row = self.layout.row()
        subrow = row.row(align=True)
        subrow.prop(self,"start")
        subrow.prop(self,"end")
        subrow = row.row()
        subrow.prop(self,"steps")
        row = self.layout.row()
        row.prop(self,"times_bool")
        split = self.layout.split()
        col = split.column()
        col.label("Location as a function of t")
        col.prop(self,"locations_bool")
        col.prop(self,"x")
        col.prop(self,"y")
        col.prop(self,"z")
        col = split.column()
        col.label("Vector as a function of t")
        col.prop(self,"vectors_bool")
        col.prop(self,"vx")
        col.prop(self,"vy")
        col.prop(self,"vz")
        col.prop(self,"n")
    
class LoadSpin(bpy.types.Operator):
    bl_idname = "spin.load"
    bl_label = "Load"
    bl_description = "Load vectors and locations from a file."
    
    state = bpy.props.IntProperty()
    file_path = bpy.props.StringProperty()

    t_start = bpy.props.StringProperty(name = "Starting time")
    t_end = bpy.props.StringProperty(name = "Ending time")
    x = bpy.props.StringProperty()
    y = bpy.props.StringProperty()
    z = bpy.props.StringProperty()
    
    def invoke(self, context, event):
        #if current file wrong -> error
        #elif current file right & is .txt but .txt wrong -> explain how it should look like
        #elif current file right & is .txt and .txt right -> load in
        #elif current file right & is .omf -> ask extra data
        
        if adjustmentMode and currentSpin != None:
            self.file_path = os.path.abspath(bpy.path.abspath(currentSpin.file_path))
            if not os.path.isfile(self.file_path):
                self.state = 0
            elif self.file_path[-4:] == ".txt":
                if LoadInText([currentSpin],self.file_path) == "FAILED!":
                    self.state = 1
                else:
                    return {'FINISHED'}
            elif self.file_path[-4:] == ".omf" or self.file_path[-4:] == ".ohf":
                self.state = 2
                self.t_start = currentSpin.t_sta_file
                self.t_end = currentSpin.t_end_file
                self.x = currentSpin.x_file
                self.y = currentSpin.y_file
                self.z = currentSpin.z_file
            else:
                self.state = 0
            return context.window_manager.invoke_props_dialog(self,width=500)
        else:
            return {'FINISHED'}

    def execute(self, context):
        if adjustmentMode and self.state == 2:
            currentSpin.t_sta_file = self.t_start
            currentSpin.t_end_file = self.t_end
            currentSpin.x_file = self.x
            currentSpin.y_file = self.y
            currentSpin.z_file = self.z
            LoadInOVF([currentSpin],self.file_path)
        return {'FINISHED'}

    def draw(self, context):
        if self.state == 0:
            text = "Invalid path! Either no file was found or the file type was "
            text = text + "not of the right type."
            self.layout.label(text)
            self.layout.label("Only .txt and .ovf files are supported.")
        elif self.state == 1:
            text = "Invalid text file! The text file should contain 7 columns of "
            text = text + "floating points seperated by tabs."
            self.layout.label(text)
            text = "This is the standard format when copy pasting excel columns "
            text = text + "into a text file.."
            self.layout.label(text)
            text = "The columns should have equal length and correspond to the times, "
            text = text + "the 3 components of the "
            self.layout.label(text)
            text =  "locations and the 3 components of the directions of the spin."
            self.layout.label(text)
        elif self.state == 2:
            text = "A .ovf file was selected. For this file type, the coordinates "
            text = text + "of the relevant cell need to be provided."
            self.layout.label(text)
            text = "Also the starting time and ending time need to be provided. "
            text = text + "Other .ovf files with the same name " 
            self.layout.label(text)
            text = "in the same directory will automatically be loaded in."
            self.layout.label(text)
            text = "The times and coordinates used this way will also be allocated "
            text = text + "as the times and locations of the "
            self.layout.label(text)
            text = "current spin. Since these values are usually too small (about 1 "
            text = text + "million times) it might be best to "
            self.layout.label(text)
            text = "later overwrite these using the Equations feature."
            self.layout.label(text)
            
            self.layout.prop(self,"t_start")
            self.layout.prop(self,"t_end")
            self.layout.prop(self,"x")
            self.layout.prop(self,"y")
            self.layout.prop(self,"z")          
            
class AddArrow(bpy.types.Operator):
    bl_idname = "arrow.add"
    bl_label = "Add Arrow"
    bl_description = "Add an arrow."

    def invoke(self, context, event):
        if adjustmentMode:
            arrow = Arrow()
            listOfArrows.append(arrow) 
            SetCurrentArrow(settings=context.scene.spinplotsettings,arrow=arrow)
        return {'FINISHED'}

class SelectArrow(bpy.types.Operator):
    bl_idname = "arrow.select"
    bl_label = "Select Arrow"
    bl_description = "Select an arrow."
    bl_options = {'REGISTER', 'UNDO'}
    name = StringProperty()

    def execute(self, context):
        if adjustmentMode:
            global currentArrow
            for a in listOfArrows:
                if a.name == self.name:
                    SetCurrentArrow(settings=context.scene.spinplotsettings,arrow=a)
        return {'FINISHED'}
    
class DeleteArrow(bpy.types.Operator):
    bl_idname = "arrow.delete"
    bl_label = "Delete Arrow"
    bl_description = "Delete the currently selected arrow."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if adjustmentMode:
            global currentArrow
            global arrowForSpinSets
            if currentArrow != None:
                listOfArrows.remove(currentArrow)
                if currentArrow == arrowForSpinSets:
                    arrowForSpinSets = None
                currentArrow.Delete()
                if len(listOfArrows) != 0:
                    SetCurrentArrow(settings=context.scene.spinplotsettings,arrow=listOfArrows[0])
                else:
                    SetCurrentArrow(settings=context.scene.spinplotsettings,arrow=None)
        return {'FINISHED'}

class SpinArrowLink(bpy.types.Operator):
    bl_idname = "link.spinarrow"
    bl_label = "Spin Arrow Link"
    bl_description = "Perform an action concerning spin arrow links."
    bl_options = {'REGISTER', 'UNDO'}
    spinName = StringProperty()
    action = StringProperty()

    def execute(self, context):
        if adjustmentMode:
            for s in listOfSpins:
                if s.name == self.spinName:
                    spin = s
            if self.action == "link":
                spin.linkedArrow = currentArrow
                if spin == currentSpin:
                    context.scene.spinplotsettings.currentSpinLinkedArrow = currentArrow.name
            elif self.action == "unlink":
                spin.linkedArrow = None
                if spin == currentSpin:
                    context.scene.spinplotsettings.currentSpinLinkedArrow = ""
        return {'FINISHED'}

class CreateSpinSet(bpy.types.Operator):
    bl_idname = "spinset.create"
    bl_label = "Equations"
    bl_description = "Create vectors and locations through equations."
    bl_options = {'REGISTER', 'UNDO'}
    
    start = bpy.props.FloatProperty()
    end = bpy.props.FloatProperty()
    steps = bpy.props.IntProperty()
    
    A_s = bpy.props.IntProperty(name = "A start")
    A_e = bpy.props.IntProperty(name = "A end")
    B_s = bpy.props.IntProperty(name = "B start")
    B_e = bpy.props.IntProperty(name = "B end")
    C_s = bpy.props.IntProperty(name = "C start")
    C_e = bpy.props.IntProperty(name = "C end")
    
    x = bpy.props.StringProperty()
    y = bpy.props.StringProperty()
    z = bpy.props.StringProperty()
    vx = bpy.props.StringProperty()
    vy = bpy.props.StringProperty()
    vz = bpy.props.StringProperty()
    n = bpy.props.StringProperty()
    
    def invoke(self, context, event):
        if adjustmentMode:
            return context.window_manager.invoke_props_dialog(self,width=500)
        else:
            return {'FINISHED'}

    def execute(self, context):
        if adjustmentMode:
            if self.A_e < self.A_s:
                self.A_e = self.A_s
            if self.B_e < self.B_s:
                self.B_e = self.B_s
            if self.C_e < self.C_s:
                self.C_e = self.C_s
            for a in range(self.A_s,self.A_e+1):
                for b in range(self.B_s,self.B_e+1):
                    for c in range(self.C_s,self.C_e+1):
                        spin = Spin()
                        eqs = [self.x,self.y,self.z,self.vx,self.vy,self.vz,self.n]
                        new_eqs = []
                        for eq in eqs:
                            temp_eq = ""
                            for char in eq:
                                if char == "A":
                                    temp_eq = temp_eq + str(a)
                                elif char == "B":
                                    temp_eq = temp_eq + str(b)
                                elif char == "C":
                                    temp_eq = temp_eq + str(c)
                                else:
                                    temp_eq = temp_eq + char
                            new_eqs.append(temp_eq)
                        spin.t_sta_eq = self.start
                        spin.t_end_eq = self.end
                        spin.t_ste_eq = self.steps
                        spin.x_eq = new_eqs[0]
                        spin.y_eq = new_eqs[1]
                        spin.z_eq = new_eqs[2]
                        spin.vx_eq = new_eqs[3]
                        spin.vy_eq = new_eqs[4]
                        spin.vz_eq = new_eqs[5]
                        spin.n_eq = new_eqs[6]
                        if spin.UseEquations() != "FAILED!":
                            listOfSpins.append(spin)
                            spin.linkedArrow = arrowForSpinSets
                            SetCurrentSpin(settings=context.scene.spinplotsettings,spin=spin)
        return {'FINISHED'}

    def draw(self, context):
        row = self.layout.row()
        row.label("Times:")
        row = self.layout.row()
        subrow = row.row(align=True)
        subrow.prop(self,"start")
        subrow.prop(self,"end")
        subrow = row.row()
        subrow.prop(self,"steps")
        row = self.layout.row()
        row.label("Iteration parameters:")
        split = self.layout.split()
        col = split.column()
        row = col.row(align=True)
        row.prop(self,"A_s")
        row.prop(self,"A_e")
        col = split.column()
        row = col.row(align=True)
        row.prop(self,"B_s")
        row.prop(self,"B_e")
        col = split.column()
        row = col.row(align=True)
        row.prop(self,"C_s")
        row.prop(self,"C_e")
        split = self.layout.split()
        col = split.column()
        col.label("Location as a function of t")
        col.prop(self,"x")
        col.prop(self,"y")
        col.prop(self,"z")
        col = split.column()
        col.label("Vector as a function of t")
        col.prop(self,"vx")
        col.prop(self,"vy")
        col.prop(self,"vz")
        col.prop(self,"n")
    
class LoadSpinSet(bpy.types.Operator):
    bl_idname = "spinset.load"
    bl_label = "Load"
    bl_description = "Load vectors and locations from a file."
    
    state = bpy.props.IntProperty()
    file_path = bpy.props.StringProperty()

    t_start_l = bpy.props.StringProperty(name = "Starting time")
    t_end_l = bpy.props.StringProperty(name = "Ending time")
    x_l = bpy.props.StringProperty(name = "x")
    y_l = bpy.props.StringProperty(name = "y")
    z_l = bpy.props.StringProperty(name = "z")
    
    t_start_a = bpy.props.StringProperty(name = "Starting time")
    t_end_a = bpy.props.StringProperty(name = "Ending time")
    x_a = bpy.props.StringProperty(name = "x")
    y_a = bpy.props.StringProperty(name = "y")
    z_a = bpy.props.StringProperty(name = "z")
    
    A_s = bpy.props.IntProperty(name = "A start")
    A_e = bpy.props.IntProperty(name = "A end")
    B_s = bpy.props.IntProperty(name = "B start")
    B_e = bpy.props.IntProperty(name = "B end")
    C_s = bpy.props.IntProperty(name = "C start")
    C_e = bpy.props.IntProperty(name = "C end")
    
    def invoke(self, context, event):
        p = context.scene.spinplotsettings.spinSetFilePath
        if adjustmentMode:
            self.file_path = os.path.abspath(bpy.path.abspath(p))
            if not os.path.isfile(self.file_path):
                self.state = 0
            elif self.file_path[-4:] == ".txt":
                if LoadInText([],self.file_path) == "FAILED!":
                    self.state = 1
                else:
                    return {'FINISHED'}
            elif self.file_path[-4:] == ".omf" or self.file_path[-4:] == ".ohf":
                self.state = 2
            else:
                self.state = 0
            return context.window_manager.invoke_props_dialog(self,width=500)
        else:
            return {'FINISHED'}

    def execute(self, context):
        if adjustmentMode and self.state == 2:
            if self.A_e < self.A_s:
                self.A_e = self.A_s
            if self.B_e < self.B_s:
                self.B_e = self.B_s
            if self.C_e < self.C_s:
                self.C_e = self.C_s
            time_eqs = [self.t_start_l,self.t_end_l,self.t_start_a,self.t_end_a]
            for i in range(0,len(time_eqs)):
                value = EvaluateEquation(time_eqs[i],[0])
                if value == "FAILED!":
                    print("FAILED! LoadSpinSet 1")
                    return {'FINISHED'}
                else:
                    time_eqs[i] = value[0]
            temp_spins = []
            spinNameIndex = 0
            for a in range(self.A_s,self.A_e+1):
                for b in range(self.B_s,self.B_e+1):
                    for c in range(self.C_s,self.C_e+1):
                        foundName = False
                        while not foundName:
                            spinNameIndex += 1
                            name = "Spin" + str(spinNameIndex)
                            foundName = True
                            for s in listOfSpins:
                                if s.name == name:
                                    foundName = False
                        spin = Spin(temp_name=name)
                        eqs = [self.x_l,self.y_l,self.z_l,self.x_a,self.y_a,self.z_a]
                        new_eqs = []
                        for eq in eqs:
                            temp_eq = ""
                            for char in eq:
                                if char == "A":
                                    temp_eq = temp_eq + str(a)
                                elif char == "B":
                                    temp_eq = temp_eq + str(b)
                                elif char == "C":
                                    temp_eq = temp_eq + str(c)
                                else:
                                    temp_eq = temp_eq + char
                            value = EvaluateEquation(temp_eq,[0])
                            if value == "FAILED!":
                                print("FAILED! LoadSpinSet 2")
                                return {'FINISHED'}
                            else:
                                new_eqs.append(str(value[0]))
                        spin.t_sta_file = time_eqs[0]
                        spin.t_end_file = time_eqs[1]
                        spin.t_sta_eq = time_eqs[2]
                        spin.t_end_eq = time_eqs[3]
                        spin.x_file = new_eqs[0]
                        spin.y_file = new_eqs[1]
                        spin.z_file = new_eqs[2]
                        spin.x_eq = new_eqs[3]
                        spin.y_eq = new_eqs[4]
                        spin.z_eq = new_eqs[5]
                        temp_spins.append(spin)
            if LoadInOVF(temp_spins,self.file_path) == "FAILED!":
                print("FAILED! LoadSpinSet 3")
                return {'FINISHED'}
            for s in temp_spins:
                new_times = []
                new_locations = []
                for i in range(0,len(s.times)):
                    if len(s.times) == 1:
                        new_times = [float(s.t_sta_eq)]
                    else:
                        new_times.append(float(s.t_sta_eq) + (float(s.t_end_eq) - float(s.t_sta_eq))*(s.times[i]-s.times[0])/(s.times[-1]-s.times[0]))
                    new_locations.append([float(s.x_eq),float(s.y_eq),float(s.z_eq)])
                s.times = new_times
                s.locations = new_locations
                listOfSpins.append(s)
                s.linkedArrow = arrowForSpinSets
                SetCurrentSpin(settings=context.scene.spinplotsettings,spin=s)
        return {'FINISHED'}

    def draw(self, context):
        if self.state == 0:
            text = "Invalid path! Either no file was found or the file type was "
            text = text + "not of the right type."
            self.layout.label(text)
            self.layout.label("Only .txt and .ovf files are supported.")
        elif self.state == 1:
            text = "Invalid text file! The text file should contain 1 time column "
            text = text + "and 6 columns per spin of floating points seperated by tabs."
            self.layout.label(text)
            text = "This is the standard format when copy pasting excel columns "
            text = text + "into a text file.."
            self.layout.label(text)
            text = "The columns should have equal length and correspond to the times, "
            text = text + "the 3 components of the "
            self.layout.label(text)
            text =  "locations and the 3 components of the directions of the spins."
            self.layout.label(text)
        elif self.state == 2:
            self.layout.label("Times:")
            split = self.layout.split()
            col = split.column()
            col.label("Load-in values")
            col.prop(self,"t_start_l")
            col.prop(self,"t_end_l")
            col = split.column()
            col.label("Allocated values")
            col.prop(self,"t_start_a")
            col.prop(self,"t_end_a")
            
            self.layout.label("Iteration parameters:")
            split = self.layout.split()
            col = split.column()
            row = col.row(align=True)
            row.prop(self,"A_s")
            row.prop(self,"A_e")
            col = split.column()
            row = col.row(align=True)
            row.prop(self,"B_s")
            row.prop(self,"B_e")
            col = split.column()
            row = col.row(align=True)
            row.prop(self,"C_s")
            row.prop(self,"C_e")
            split = self.layout.split()
            
            self.layout.label("Locations:")
            split = self.layout.split()
            col = split.column()
            col.label("Load-in values")
            col.prop(self,"x_l")
            col.prop(self,"y_l")
            col.prop(self,"z_l")
            col = split.column()
            col.label("Allocated values")
            col.prop(self,"x_a")
            col.prop(self,"y_a")
            col.prop(self,"z_a")
            
class SpinSetArrowLink(bpy.types.Operator):
    bl_idname = "link.spinsetarrow"
    bl_label = "Spin Set Arrow Link"
    bl_description = "Link an arrow to a spin set."
    bl_options = {'REGISTER', 'UNDO'}
    arrowName = StringProperty()
    
    def execute(self, context):
        if adjustmentMode:
            for a in listOfArrows:
                if a.name == self.arrowName:
                    global arrowForSpinSets
                    arrowForSpinSets = a
        return {'FINISHED'}

#############################
#                           #
#           MENUS           #
#                           #
#############################

class SpinsMenu(bpy.types.Menu):
    bl_idname = "menu.spins"
    bl_label = "Spins"

    def draw(self, context):
        for s in listOfSpins:
            text = s.name
            op = self.layout.operator("spin.select", text=text)
            op.name = text

class ArrowsMenu(bpy.types.Menu):
    bl_idname = "menu.arrows"
    bl_label = "Arrows"

    def draw(self, context):
        for a in listOfArrows:
            text = a.name
            op = self.layout.operator("arrow.select", text=text)
            op.name = text

class ArrowLinksMenu(bpy.types.Menu):
    bl_idname = "menu.arrowlinks"
    bl_label = "Linked Spins"

    def draw(self, context):
        for s in listOfSpins:
            if s.linkedArrow == currentArrow:
                text = s.name
                op = self.layout.operator("link.spinarrow", text=text)
                op.spinName = text
                op.action = "list"
            
class ArrowLinkMenu(bpy.types.Menu):
    bl_idname = "menu.arrowlink"
    bl_label = "Link Spin"

    def draw(self, context):
        for s in listOfSpins:
            if s.linkedArrow != currentArrow:
                text = s.name
                op = self.layout.operator("link.spinarrow", text=text)
                op.spinName = text
                op.action = "link"
            
class ArrowUnlinkMenu(bpy.types.Menu):
    bl_idname = "menu.arrowunlink"
    bl_label = "Unlink Spin"

    def draw(self, context):
        for s in listOfSpins:
            if s.linkedArrow == currentArrow:
                text = s.name
                op = self.layout.operator("link.spinarrow", text=text)
                op.spinName = text
                op.action = "unlink"
                
class SpinSetLinkMenu(bpy.types.Menu):
    bl_idname = "menu.spinsetlink"
    bl_label = "Select Arrow to link to Spins"

    def draw(self, context):
        for a in listOfArrows:
            text = a.name
            op = self.layout.operator("link.spinsetarrow", text=text)
            op.arrowName = text

#############################
#                           #
#           PANELS          #
#                           #
#############################
            
class GeneralPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_general_panel"
    bl_label = "General"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"
    bl_category = "Spin Plot"
    
    def draw(self, context):
        scene = context.scene
        spinplotsettings = scene.spinplotsettings
        
#        row = self.layout.row()
#        row.prop(scene, "frame_start")
#        row.prop(scene, "frame_end")
#        self.layout.label(text="Hello World")
        self.layout.prop(spinplotsettings,"resetOnCreate")
        row = self.layout.row(align=True)
        row.operator("scene.create")
        row.operator("scene.adjust")
        row = self.layout.row(align=True)
        row.prop(spinplotsettings,"startingTime")
        row.prop(spinplotsettings,"endingTime")

class SpinPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_spin_panel"
    bl_label = "Spins"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"
    bl_category = "Spin Plot"
    
    def draw(self, context):
        scene = context.scene
        spinplotsettings = scene.spinplotsettings
        self.layout.menu("menu.spins",text="Select Spin")
        self.layout.operator("spin.add")
        self.layout.prop(spinplotsettings,"currentSpinName")
        self.layout.prop(spinplotsettings,"currentSpinLinkedArrow")
        col = self.layout.column(align=True)
        col.operator("spin.view")
        col.operator("spin.create")
        rowincol = col.row(align=True)
        rowincol.operator("spin.load")
        rowincol.prop(spinplotsettings,"currentSpinFilePath")
        self.layout.operator("spin.delete")
        
            
class ArrowPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_arrow_panel"
    bl_label = "Arrows"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"
    bl_category = "Spin Plot"
    
    def draw(self, context):
        scene = context.scene
        spinplotsettings = scene.spinplotsettings
        self.layout.menu("menu.arrows",text="Select Arrow")
        self.layout.operator("arrow.add")
        self.layout.prop(spinplotsettings,"currentArrowName")
        
        col = self.layout.column(align=True)
        col.menu("menu.arrowlinks",text="Linked Spins")
        rowincol = col.row(align=True)
        rowincol.menu("menu.arrowlink",text="Link Spin")
        rowincol.menu("menu.arrowunlink",text="Unlink Spin")
        self.layout.operator("arrow.delete")
        
class AdvancedPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_advanced_panel"
    bl_label = "Advanced"
    bl_space_type = "VIEW_3D"   
    bl_region_type = "TOOLS"
    bl_category = "Spin Plot"
    
    def draw(self, context):
        scene = context.scene
        spinplotsettings = scene.spinplotsettings
        self.layout.label("Create spin set")
        col = self.layout.column(align=True)
        col.operator("spinset.create")
        rowincol = col.row(align=True)
        rowincol.operator("spinset.load")
        rowincol.prop(spinplotsettings,"spinSetFilePath")
        col.menu("menu.spinsetlink",text="Select Arrow to link")

#############################
#                           #
#         FUNCTIONS         #
#                           #
#############################

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.spinplotsettings = PointerProperty(type=SpinPlotSettings)

def unregister():
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.spinplotsettings
    
def SetCurrentSpin(settings,spin):
    global currentSpin 
    #if currentSpin != None:
        #currentSpin.Deselect()
    currentSpin = spin
    if spin != None:
        #spin.Select()
        settings.currentSpinName = spin.name
        if spin.linkedArrow == None:
            settings.currentSpinLinkedArrow = ""
        else:
            settings.currentSpinLinkedArrow = spin.linkedArrow.name
        settings.currentSpinFilePath = spin.file_path
    else:
        settings.currentSpinName = ""
        settings.currentSpinLinkedArrow = ""
    
def SetCurrentArrow(settings,arrow):
    global currentArrow
    if currentArrow != None:
        currentArrow.Deselect()
    currentArrow = arrow
    if arrow != None:
        arrow.Select()
        settings.currentArrowName = arrow.name
    else:
        settings.currentArrowName = ""
        
def EvaluateEquation(eq,times):
    index = 0
    while index < len(eq):
        if eq[index] == " ":
            eq = eq[0:index] + eq[index+1:]
        index += 1
    
    index = 0
    subEvaluateStart = 0
    intermediateSubEvaluates = 0
    subEvaluates = []
    while index < len(eq):
        if eq[index] == "(":
            if intermediateSubEvaluates == 0:
                subEvaluateStart = index
            intermediateSubEvaluates += 1 
        elif eq[index] == ")":
            if intermediateSubEvaluates == 0:
                return "FAILED!"
            elif intermediateSubEvaluates == 1:
                evaluation = EvaluateEquation(eq[subEvaluateStart+1:index],times)
                if evaluation == "FAILED!":
                    return "FAILED!"
                else:
                    preEvaluate = eq[subEvaluateStart-3:subEvaluateStart]
                    if preEvaluate == "exp":
                        tempEvaluation = []
                        for i in range(0,len(evaluation)):
                            tempEvaluation.append(math.exp(evaluation[i]))
                        evaluation = tempEvaluation
                        subEvaluates.append((tempEvaluation,subEvaluateStart-3,index))
                    elif preEvaluate == "cos":
                        tempEvaluation = []
                        for i in range(0,len(evaluation)):
                            tempEvaluation.append(math.cos(evaluation[i]))
                        evaluation = tempEvaluation
                        subEvaluates.append((tempEvaluation,subEvaluateStart-3,index))
                    elif preEvaluate == "sin":
                        tempEvaluation = []
                        for i in range(0,len(evaluation)):
                            tempEvaluation.append(math.sin(evaluation[i]))
                        evaluation = tempEvaluation
                        subEvaluates.append((tempEvaluation,subEvaluateStart-3,index))
                    else:
                        subEvaluates.append((evaluation,subEvaluateStart,index))
            intermediateSubEvaluates -= 1
        index += 1
    if intermediateSubEvaluates > 0:
        return "FAILED!"
    
    index = 0
    numbers = {"0","1","2","3","4","5","6","7","8","9"}
    while index < len(eq):
        if eq[index] == ".":
            passed = True
            for s in subEvaluates:
                if index >= s[1] and index <= s[2]:
                    passed = False
            if passed:
                subIndex1 = 1
                while index - subIndex1 >= 0 and eq[index - subIndex1] in numbers:
                    subIndex1 += 1
                subIndex2 = 1
                while index + subIndex2 < len(eq) and eq[index + subIndex2] in numbers:
                    subIndex2 += 1
                if subIndex1 == 1 or subIndex2 == 1:
                    return "FAILED!"
                else:
                    values = []    
                    val = float(eq[index-subIndex1+1:index+subIndex2])
                    for i in range(0,len(times)):
                        values.append(val)
                    subEvaluates.append((values,index-subIndex1+1,index+subIndex2-1))
        index += 1
    
    index = len(eq)-1
    while index >= 0:
        if eq[index] == "e" or eq[index] == "^":
            passed = True
            leftEvaluate = None
            rightEvaluate = None
            for s in subEvaluates:
                if index >= s[1] and index <= s[2]:
                    passed = False
                if index == s[1]-1:
                    rightEvaluate = s
                elif index == s[2]+1:
                    leftEvaluate = s
            if passed:
                if leftEvaluate != None:
                    subEvaluates.remove(leftEvaluate)
                else:
                    subIndex = 1
                    while index - subIndex >= 0 and eq[index - subIndex] in numbers:
                        subIndex += 1
                    if subIndex == 1:
                        if eq[index - 1] == "t" and index != 0:
                            leftEvaluate = (times,index-1,index-1)
                        else:
                            return "FAILED!"
                    else:
                        values = []    
                        val = float(eq[index-subIndex+1:index])
                        for i in range(0,len(times)):
                            values.append(val)
                        leftEvaluate = (values,index-subIndex+1,index-1)
                if rightEvaluate != None:
                    subEvaluates.remove(rightEvaluate)
                else:
                    subIndex = 1
                    if index + 2 < len(eq):
                        if eq[index + 1] == "-" and eq[index + 2] in numbers:
                            subIndex = 2
                    while index + subIndex < len(eq) and eq[index + subIndex] in numbers:
                        subIndex += 1
                    if subIndex == 1:
                        if index != len(eq)-1 and eq[index + 1] == "t":
                            rightEvaluate = (times,index+1,index+1)
                        else:
                            return "FAILED!"
                    else:
                        values = []    
                        val = float(eq[index+1:index+subIndex])
                        for i in range(0,len(times)):
                            values.append(val)
                        rightEvaluate = (values,index+1,index+subIndex-1)
                values = []
                for i in range(0,len(times)):
                    if eq[index] == "e":
                        values.append(leftEvaluate[0][i]*10**(rightEvaluate[0][i]))
                    elif eq[index] == "^":
                        values.append(leftEvaluate[0][i]**(rightEvaluate[0][i]))
                subEvaluates.append((values,leftEvaluate[1],rightEvaluate[2]))
        index -= 1

    index = 0
    while index < len(eq):
        if eq[index] == "*" or eq[index] == "/":
            passed = True
            leftEvaluate = None
            rightEvaluate = None
            for s in subEvaluates:
                if index >= s[1] and index <= s[2]:
                    passed = False
                if index == s[1]-1:
                    rightEvaluate = s
                elif index == s[2]+1:
                    leftEvaluate = s
            if passed:
                if leftEvaluate != None:
                    subEvaluates.remove(leftEvaluate)
                else:
                    subIndex = 1
                    while index - subIndex >= 0 and eq[index - subIndex] in numbers:
                        subIndex += 1
                    if subIndex == 1:
                        if eq[index - 1] == "t" and index != 0:
                            leftEvaluate = (times,index-1,index-1)
                        else:
                            return "FAILED!"
                    else:
                        values = []    
                        val = float(eq[index-subIndex+1:index])
                        for i in range(0,len(times)):
                            values.append(val)
                        leftEvaluate = (values,index-subIndex+1,index-1)
                if rightEvaluate != None:
                    subEvaluates.remove(rightEvaluate)
                else:
                    subIndex = 1
                    while index + subIndex < len(eq) and eq[index + subIndex] in numbers:
                        subIndex += 1
                    if subIndex == 1:
                        if index != len(eq)-1 and eq[index + 1] == "t":
                            rightEvaluate = (times,index+1,index+1)
                        else:
                            return "FAILED!"
                    else:
                        values = []    
                        val = float(eq[index+1:index+subIndex])
                        for i in range(0,len(times)):
                            values.append(val)
                        rightEvaluate = (values,index+1,index+subIndex-1)
                values = []
                for i in range(0,len(times)):
                    if eq[index] == "*":
                        values.append(leftEvaluate[0][i]*(rightEvaluate[0][i]))
                    elif eq[index] == "/":
                        if rightEvaluate[0][i] == 0.0:
                            return "FAILED!"
                        values.append(leftEvaluate[0][i]/(rightEvaluate[0][i]))
                subEvaluates.append((values,leftEvaluate[1],rightEvaluate[2]))
        index += 1

    index = 0
    while index < len(eq):
        if eq[index] == "+" or eq[index] == "-":
            passed = True
            leftEvaluate = None
            rightEvaluate = None
            for s in subEvaluates:
                if index >= s[1] and index <= s[2]:
                    passed = False
                if index == s[1]-1:
                    rightEvaluate = s
                elif index == s[2]+1:
                    leftEvaluate = s
            if passed:
                if leftEvaluate != None:
                    subEvaluates.remove(leftEvaluate)
                else:
                    subIndex = 1
                    while index - subIndex >= 0 and eq[index - subIndex] in numbers:
                        subIndex += 1
                    if subIndex == 1:
                        if index == 0  and eq[index] == "-":
                            values = []
                            for i in range(0,len(times)):
                                values.append(0)
                            leftEvaluate = (values,0,0)
                        elif eq[index - 1] == "t":
                            leftEvaluate = (times,index-1,index-1)
                        else:
                            return "FAILED!"
                    else:
                        values = []    
                        val = float(eq[index-subIndex+1:index])
                        for i in range(0,len(times)):
                            values.append(val)
                        leftEvaluate = (values,index-subIndex+1,index-1)
                if rightEvaluate != None:
                    subEvaluates.remove(rightEvaluate)
                else:
                    subIndex = 1
                    while index + subIndex < len(eq) and eq[index + subIndex] in numbers:
                        subIndex += 1
                    if subIndex == 1:
                        if index != len(eq)-1 and eq[index + 1] == "t":
                            rightEvaluate = (times,index+1,index+1)
                        else:
                            return "FAILED!"
                    else:
                        values = []    
                        val = float(eq[index+1:index+subIndex])
                        for i in range(0,len(times)):
                            values.append(val)
                        rightEvaluate = (values,index+1,index+subIndex-1)
                values = []
                for i in range(0,len(times)):
                    if eq[index] == "+":
                        values.append(leftEvaluate[0][i]+(rightEvaluate[0][i]))
                    elif eq[index] == "-":
                        values.append(leftEvaluate[0][i]-(rightEvaluate[0][i]))
                subEvaluates.append((values,leftEvaluate[1],rightEvaluate[2]))
        index += 1
    
    if len(subEvaluates) != 0 and subEvaluates[0][1] == 0 and subEvaluates[0][2] == len(eq)-1:
        return subEvaluates[0][0]
    else:
        try:
            values = []
            val = int(eq)
            for i in range(0,len(times)):
                values.append(val)
            return values
        except:
            if eq == "t":
                return times
            else:
                return "FAILED!"
            
def LoadInText(spins,path):
    lines = open(path,"r").readlines()
    numberOfColumns = 0
    data = []
    for char in lines[0]:
        if char == "\t" or char == "\n":
            numberOfColumns += 1
            data.append([])
    if numberOfColumns != len(spins)*6+1:
        print("FAILED! LoadInText 1")
        return "FAILED!"
    for line in lines:
        word = ""
        index = 0
        for char in line:
            if char == "\t" or char == "\n":
                if word != "":
                    try:
                        data[index].append(float(word))
                    except:
                        print("FAILED! LoadInText 2")
                        return "FAILED!"
                    index += 1
                    word = ""
            else:
                word = word + char
        if word != "":
            try:
                data[index].append(float(word))
            except:
                print("FAILED! LoadInText 3")
                return "FAILED!"
        if index < numberOfColumns and index != 0:
            print("FAILED! LoadInText 4")
            return "FAILED!"
    index = 0
    for s in spins:
        index += 1
        s.times = data[0]
        s.locations = []
        s.vectors = []
        for i in range(0,len(data[0])):
            s.locations.append([data[index*6-5][i],data[index*6-4][i],data[index*6-3][i]])
            s.vectors.append([data[index*6-2][i],data[index*6-1][i],data[index*6][i]])

def LoadInOVF(spins,path):
    p = path[0:len(path)-22] + "*" + path[-4:]
    files = sorted(glob.glob(p))
    data = []
    for i in range(0,len(spins)):
        try:
            float(spins[i].x_file)
            float(spins[i].y_file)
            float(spins[i].z_file)
            float(spins[i].t_sta_file)
            float(spins[i].t_end_file)
        except:
            print("FAILED! LoadInOVF 1")
            return "FAILED!"
        data.append([])
    for f in files:
        print("Load in: " + str(f))
        lines = open(f,"r").readlines()
        time = ""
        dataLine = ""
        mesh_type = ""
        for i in range(0,len(lines)):
            l = lines[i]
            if "Total simulation time" in l:
                word = ""
                check = True
                index = len(l)
                while check:
                    index -= 1
                    if l[index] == ":":
                        check = False
                    elif l[index] != "s":
                        word = l[index] + word
                try:
                    time = float(word)
                except:
                    print("FAILED! LoadInOVF 2")
                    return "FAILED!"
            if "meshtype" in l:
                if "rectangular" in l:
                    mesh_type = "rectangular"
                elif "irregular" in l:
                    mesh_type = "irregular"
                else:
                    print("FAILED! LoadInOVF 3")
                    return "FAILED!"
            if "Begin: Data Text" in l:
                dataLine = i+1
        if time == "" or dataLine == "" or mesh_type == "":
            print("FAILED! LoadInOVF 4")
            return "FAILED!"
        index = 0
        rectSettings = {"x_s":"","y_s":"","z_s":"","d_x":"","d_y":"","d_z":"","n_x":"","n_y":"","n_z":""}
        while "Begin: Data Text" not in lines[index] and index < len(lines):
            index += 1
            number = ""
            for char in lines[index]:
                if char == ":":
                    number = ""
                elif char != " " and char != "s":
                    number = number + char
            if "." in number or "e" in number:
                try:
                    number = float(number)
                except:
                    pass
            else:
                try:
                    number = int(number)
                except:
                    pass
            if "xmin" in lines[index]:
                rectSettings["x_s"] = number
            elif "xstepsize" in lines[index]:
                rectSettings["d_x"] = number
            elif "xnodes" in lines[index]:
                rectSettings["n_x"] = int(number)
            elif "ymin" in lines[index]:
                rectSettings["y_s"] = number
            elif "ystepsize" in lines[index]:
                rectSettings["d_y"] = number
            elif "ynodes" in lines[index]:
                rectSettings["n_y"] = number
            elif "zmin" in lines[index]:
                rectSettings["z_s"] = number
            elif "zstepsize" in lines[index]:
                rectSettings["d_z"] = number
            elif "znodes" in lines[index]:
                rectSettings["n_z"] = number
        if mesh_type == "rectangular" and "" in rectSettings.values():
            print("FAILED! LoadInOVF 5")
            return "FAILED!"
        elif mesh_type == "irregular" and "" in [rectSettings["d_x"],rectSettings["d_y"],rectSettings["d_z"]]:
            print("FAILED! LoadInOVF 6")
            return "FAILED!"
        if mesh_type == "rectangular":
            for i in range(0,len(spins)):
                t_s = float(spins[i].t_sta_file)
                t_e = float(spins[i].t_end_file)
                if time < t_s or time > t_e:
                    continue
                x = float(spins[i].x_file)
                y = float(spins[i].y_file)
                z = float(spins[i].z_file)
                
                if x < rectSettings["x_s"] or x > rectSettings["x_s"] + rectSettings["n_x"]*rectSettings["d_x"] or \
                y < rectSettings["y_s"] or y > rectSettings["y_s"] + rectSettings["n_y"]*rectSettings["d_y"] or \
                z < rectSettings["z_s"] or z > rectSettings["z_s"] + rectSettings["n_z"]*rectSettings["d_z"]:
                    print("FAILED! LoadInOVF 7")
                    print([x,y,z])
                    return "FAILED!"
                indexDesiredLine = dataLine
                indexDesiredLine += int((x-rectSettings["x_s"])/rectSettings["d_x"])
                indexDesiredLine += rectSettings["n_x"]*int((y-rectSettings["y_s"])/rectSettings["d_y"])
                indexDesiredLine += rectSettings["n_x"]*rectSettings["n_y"]*int((z-rectSettings["z_s"])/rectSettings["d_z"])
                
                word = ""
                state = 0
                vx = 0
                vy = 0
                vz = 0
                try:
                    for char in lines[indexDesiredLine][1:]:
                        if char == " ":
                            if state == 0:
                                vx = float(word)
                                word = ""
                                state = 1
                            elif state == 1:
                                vy = float(word)
                                word = ""
                        elif char == "\n":
                            vz = float(word)
                        else:
                            word = word + char
                except:
                    print("FAILED! LoadInOVF 8")
                    return "FAILED!"
                data[i].append([time,vx,vy,vz])
        else:
            for i in range(0,len(spins)):
                t_s = float(spins[i].t_sta_file)
                t_e = float(spins[i].t_end_file)
                if time < t_s or time > t_e:
                    continue
                x = float(spins[i].x_file)
                y = float(spins[i].y_file)
                z = float(spins[i].z_file)
                
                indexStartingLine = dataLine
                word = ""
                startingLineValues = []
                try:
                    for char in lines[indexStartingLine]:
                        if char == " " or char == "\n":
                            if word != "":
                                startingLineValues.append(word)
                                word = ""
                        else:
                            word = word + char
                except:
                    print("FAILED! LoadInOVF 9")
                    return "FAILED!"
                if len(startingLineValues) != 6:
                    print("FAILED! LoadInOVF 10")
                    return "FAILED!"
                
                indexEndingLine = len(lines)-1
                while "# End: Data Text" not in lines[indexEndingLine]:
                    indexEndingLine -= 1
                    if indexEndingLine == 0:
                        print("FAILED! LoadInOVF 11")
                        return "FAILED!"
                indexEndingLine -= 1
                word = ""
                endingLineValues = []
                try:
                    for char in lines[indexEndingLine]:
                        if char == " " or char == "\n":
                            if word != "":
                                endingLineValues.append(word)
                                word = ""
                        else:
                            word = word + char
                except:
                    print("FAILED! LoadInOVF 12")
                    return "FAILED!"
                if len(endingLineValues) != 6:
                    print("FAILED! LoadInOVF 13")
                    return "FAILED!"
                
                found = False
                
                while indexEndingLine - indexStartingLine > 1 and not found:
                    indexDesiredLine = (indexStartingLine + indexEndingLine)//2
                    desiredLineValues = []
                    try:
                        for char in lines[indexDesiredLine]:
                            if char == " " or char == "\n":
                                if word != "":
                                    desiredLineValues.append(float(word))
                                    word = ""
                            else:
                                word = word + char
                    except:
                        print("FAILED! LoadInOVF 14")
                        return "FAILED!"
                    
                    if desiredLineValues[2] >= z + rectSettings["d_z"]:
                        indexEndingLine = indexDesiredLine
                        endingLineValues = desiredLineValues
                    elif desiredLineValues[2] <= z - rectSettings["d_z"]:
                        indexStartingLine = indexDesiredLine
                        startingLineValues = desiredLineValues
                    else:
                        if desiredLineValues[1] >= y + rectSettings["d_y"]:
                            indexEndingLine = indexDesiredLine
                            endingLineValues = desiredLineValues
                        elif desiredLineValues[1] <= y - rectSettings["d_y"]:
                            indexStartingLine = indexDesiredLine
                            startingLineValues = desiredLineValues
                        else:
                            if desiredLineValues[0] >= x + rectSettings["d_x"]:
                                indexEndingLine = indexDesiredLine
                                endingLineValues = desiredLineValues
                            elif desiredLineValues[0] <= x - rectSettings["d_x"]:
                                indexStartingLine = indexDesiredLine
                                startingLineValues = desiredLineValues
                            else:
                                found = True
                if not found:
                    print("FAILED! LoadInOVF 15")
                    return "FAILED!"   
                data[i].append([time,desiredLineValues[3],desiredLineValues[4],desiredLineValues[5]])
    for i in range(0,len(spins)):
        spins[i].times = []
        spins[i].locations = []
        spins[i].vectors = []
    for i in range(0,len(spins)):
        for d in data[i]:
            spins[i].times.append(d[0])
            spins[i].locations.append([float(spins[i].x_file),float(spins[i].y_file),float(spins[i].z_file)])
            spins[i].vectors.append([d[1],d[2],d[3]])

def CheckProperties(scene):
    settings = scene.spinplotsettings
    
    global currentSpin
    if currentSpin != None:
        if settings.currentSpinName != currentSpin.name:
            if adjustmentMode:
                passed = True
                for s in listOfSpins:
                    if settings.currentSpinName == s.name:
                        passed = False
                if passed:
                    currentSpin.name = settings.currentSpinName
                else:
                    settings.currentSpinName = currentSpin.name
            else:
                settings.currentSpinName = currentSpin.name
        if currentSpin.linkedArrow != None:
            if settings.currentSpinLinkedArrow != currentSpin.linkedArrow.name:
                if adjustmentMode:
                    passed = False
                    for a in listOfArrows:
                        if settings.currentSpinLinkedArrow == a.name:
                            currentSpin.linkedArrow = a
                            passed = True
                    if not passed:
                        if settings.currentSpinLinkedArrow == "":
                            currentSpin.linkedArrow = None
                        else:
                            settings.currentSpinLinkedArrow = currentSpin.linkedArrow.name
                else:
                    settings.currentSpinLinkedArrow = currentSpin.linkedArrow.name
            
        else:
            if settings.currentSpinLinkedArrow != "":
                if adjustmentMode:
                    passed = False
                    for a in listOfArrows:
                        if settings.currentSpinLinkedArrow == a.name:
                            currentSpin.linkedArrow = a
                            passed = True
                    if not passed:
                        settings.currentSpinLinkedArrow = ""
                else:
                    settings.currentSpinLinkedArrow = ""
        if settings.currentSpinFilePath != currentSpin.file_path:
            if adjustmentMode:
                currentSpin.file_path = settings.currentSpinFilePath
            else:
                settings.currentSpinFilePath = currentSpin.file_path
            
    global currentArrow
    if currentArrow != None and settings.currentArrowName != currentArrow.name:
        passed = True
        for a in listOfArrows:
            if settings.currentArrowName == a.name:
                passed = False
        if passed:
            currentArrow.SetName(settings.currentArrowName)
        else:
            settings.currentArrowName = currentArrow.name
            
def AnimateSpins(scene):
    t0 = scene.spinplotsettings.startingTime
    tf = scene.spinplotsettings.endingTime
    f0 = scene.frame_start
    ff = scene.frame_end
    frame = scene.frame_current
    if f0 < ff:
        t = t0 + (tf-t0)*(frame-f0)/(ff-f0)
    else:
        t = t0
        
    for s in listOfSpins:
        if s.object != None:
            arrow = s.object
            
            found = False
            index = 0
            weighting = 0.0
            while not found:
                if s.times[index] > t:
                    found = True
                    if index != 0:
                        index -= 1
                        weighting = (t-s.times[index])/(s.times[index+1]-s.times[index])
                else:
                    index += 1
                    if index == len(s.times):
                        found = True
                        index -= 2
                        weighting = 1.0
            vector = [0,0,0]
            for i in range(0,3):
                arrow.location[i] = s.locations[index][i]*(1-weighting) + s.locations[index+1][i]*weighting
                vector[i] = s.vectors[index][i]*(1-weighting) + s.vectors[index+1][i]*weighting
            norm = math.sqrt(vector[0]**2 + vector[1]**2 + vector[2]**2)
            point = [vector[0]/norm,vector[1]/norm,vector[2]/norm]
            if point[0] == 0:
                if point[1] > 0:
                    angle = math.pi
                else:
                    angle = 0
            else:
                angle = math.atan(point[1]/point[0])
                if point[0] > 0:
                    angle += math.pi/2
                else:
                    angle -= math.pi/2
            arrow.rotation_euler = (math.acos(point[2]), 0, angle)

if __name__ == "__main__":
    register()
    bpy.app.handlers.scene_update_post.append(CheckProperties)
    bpy.app.handlers.frame_change_pre.append(AnimateSpins)

