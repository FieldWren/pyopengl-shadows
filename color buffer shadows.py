import math
import glfw
import glfw.GLFW as GLFW_CONSTANTS
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram,compileShader
import numpy as np
import pyrr
import ctypes
from PIL import Image, ImageOps
from typing import List


############################## Constants ######################################

SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480

RETURN_ACTION_CONTINUE = 0
RETURN_ACTION_EXIT = 1

#0: debug, 1: production
GAME_MODE = 0

############################## helper functions ###############################

def initialize_glfw():

    glfw.init()
    glfw.window_hint(GLFW_CONSTANTS.GLFW_CONTEXT_VERSION_MAJOR,3)
    glfw.window_hint(GLFW_CONSTANTS.GLFW_CONTEXT_VERSION_MINOR,3)
    glfw.window_hint(GLFW_CONSTANTS.GLFW_OPENGL_PROFILE, GLFW_CONSTANTS.GLFW_OPENGL_CORE_PROFILE)
    glfw.window_hint(GLFW_CONSTANTS.GLFW_OPENGL_FORWARD_COMPAT, GLFW_CONSTANTS.GLFW_TRUE)
    #for uncapped framerate
    glfw.window_hint(GLFW_CONSTANTS.GLFW_DOUBLEBUFFER,GL_FALSE) 
    window = glfw.create_window(SCREEN_WIDTH, SCREEN_HEIGHT, "Title", None, None)
    glfw.make_context_current(window)

    return window

###############################################################################


class SimpleComponent:


    def __init__(self, position, eulers):

        self.position = np.array(position, dtype=np.float32)
        self.eulers = np.array(eulers, dtype=np.float32)

class Light:


    def __init__(self, position, color, strength):

        self.position = np.array(position, dtype=np.float32)
        self.color = np.array(color, dtype=np.float32)
        self.strength = strength

class Player:


    def __init__(self, position):

        self.position = np.array(position, dtype = np.float32)
        self.theta = 0
        self.phi = 0
        self.update_vectors()
    
    def update_vectors(self):

        self.forwards = np.array(
            [
                np.cos(np.deg2rad(self.theta)) * np.cos(np.deg2rad(self.phi)),
                np.sin(np.deg2rad(self.theta)) * np.cos(np.deg2rad(self.phi)),
                np.sin(np.deg2rad(self.phi))
            ],
            dtype = np.float32
        )

        globalUp = np.array([0,0,1], dtype=np.float32)

        self.right = np.cross(self.forwards, globalUp)

        self.up = np.cross(self.right, self.forwards)

class Scene:


    def __init__(self):

        self.bulb = SimpleComponent(position = [6, 0, 0],
                         eulers = [0, 0, 0])
        self.shade = SimpleComponent(position = [6, 0, 0],
                         eulers = [0, 0, 0])
        self.base = SimpleComponent(position = [6, 0, 0],
                         eulers = [0, 0, 0])
        self.ground = SimpleComponent(position = [0, 0, -2],
                         eulers = [0, 0, 0])
        
        self.moveable_object = SimpleComponent(position = [2, 0, -1],
                                               eulers = [0, 0, 0])

        self.lights = [Light(
            position = [6, 0, 4.6], 
            color = [247/256, 235/256, 176/256], 
            strength = 20
        )]

        self.player = Player(
            position = [0,0,2]
        )

    def update(self, rate):
        pass

    def move_object(self, dPos):
        dPos = np.array(dPos, dtype = np.float32)
        self.moveable_object.position += dPos

    def move_player(self, dPos):

        dPos = np.array(dPos, dtype = np.float32)
        self.player.position += dPos
    
    def spin_player(self, dTheta, dPhi):

        self.player.theta += dTheta
        if self.player.theta > 360:
            self.player.theta -= 360
        elif self.player.theta < 0:
            self.player.theta += 360
        
        self.player.phi = min(
            89, max(-89, self.player.phi + dPhi)
        )
        self.player.update_vectors()

class App:


    def __init__(self, window):

        self.window = window

        self.renderer = GraphicsEngine()

        self.scene = Scene()

        self.lastTime = glfw.get_time()
        self.currentTime = 0
        self.numFrames = 0
        self.frameTime = 0

        glfw.set_input_mode(self.window, GLFW_CONSTANTS.GLFW_CURSOR, GLFW_CONSTANTS.GLFW_CURSOR_HIDDEN)

        self.mainLoop()

    def mainLoop(self):
        running = True
        while (running):
            #check events
            if glfw.window_should_close(self.window) \
                or glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_ESCAPE) == GLFW_CONSTANTS.GLFW_PRESS:
                running = False
            
            self.handleKeys()
            self.handleArrowKeys()
            self.handleMouse()

            glfw.poll_events()

            self.scene.update(self.frameTime / 16.67)
            
            self.renderer.render(self.scene)

            #timing
            self.calculateFramerate()
        self.quit()

    def handleKeys(self):

        combo = 0
        directionModifier = 0
        """
        w: 1 -> 0 degrees
        a: 2 -> 90 degrees
        w & a: 3 -> 45 degrees
        s: 4 -> 180 degrees
        w & s: 5 -> x
        a & s: 6 -> 135 degrees
        w & a & s: 7 -> 90 degrees
        d: 8 -> 270 degrees
        w & d: 9 -> 315 degrees
        a & d: 10 -> x
        w & a & d: 11 -> 0 degrees
        s & d: 12 -> 225 degrees
        w & s & d: 13 -> 270 degrees
        a & s & d: 14 -> 180 degrees
        w & a & s & d: 15 -> x
        """

        up_down = 0

        if glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_W) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 1
        if glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_A) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 2
        if glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_S) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 4
        if glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_D) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 8
        
        if combo > 0:
            if combo == 3:
                directionModifier = 45
            elif combo == 2 or combo == 7:
                directionModifier = 90
            elif combo == 6:
                directionModifier = 135
            elif combo == 4 or combo == 14:
                directionModifier = 180
            elif combo == 12:
                directionModifier = 225
            elif combo == 8 or combo == 13:
                directionModifier = 270
            elif combo == 9:
                directionModifier = 315
            
            dPos = [
                self.frameTime * 0.025 * np.cos(np.deg2rad(self.scene.player.theta + directionModifier)),
                self.frameTime * 0.025 * np.sin(np.deg2rad(self.scene.player.theta + directionModifier)),
                0
            ]

            self.scene.move_player(dPos)

    
    def handleArrowKeys(self):

        combo = 0
        directionModifier = 0
        """
        w: 1 -> 0 degrees
        a: 2 -> 90 degrees
        w & a: 3 -> 45 degrees
        s: 4 -> 180 degrees
        w & s: 5 -> x
        a & s: 6 -> 135 degrees
        w & a & s: 7 -> 90 degrees
        d: 8 -> 270 degrees
        w & d: 9 -> 315 degrees
        a & d: 10 -> x
        w & a & d: 11 -> 0 degrees
        s & d: 12 -> 225 degrees
        w & s & d: 13 -> 270 degrees
        a & s & d: 14 -> 180 degrees
        w & a & s & d: 15 -> x
        """

        if glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_UP) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 1
        if glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_LEFT) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 2
        if glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_DOWN) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 4
        if glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_RIGHT) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 8
        
        if combo > 0:
            if combo == 3:
                directionModifier = 45
            elif combo == 2 or combo == 7:
                directionModifier = 90
            elif combo == 6:
                directionModifier = 135
            elif combo == 4 or combo == 14:
                directionModifier = 180
            elif combo == 12:
                directionModifier = 225
            elif combo == 8 or combo == 13:
                directionModifier = 270
            elif combo == 9:
                directionModifier = 315
            
            dPos = [
                self.frameTime * 0.025 * np.cos(np.deg2rad(self.scene.player.theta + directionModifier)),
                self.frameTime * 0.025 * np.sin(np.deg2rad(self.scene.player.theta + directionModifier)),
                0
            ]

            self.scene.move_object(dPos)

    def handleMouse(self):

        (x,y) = glfw.get_cursor_pos(self.window)
        rate = self.frameTime / 16.67
        theta_increment = rate * ((SCREEN_WIDTH / 2) - x)
        phi_increment = rate * ((SCREEN_HEIGHT / 2) - y)
        self.scene.spin_player(theta_increment, phi_increment)
        glfw.set_cursor_pos(self.window, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    def calculateFramerate(self):

        self.currentTime = glfw.get_time()
        delta = self.currentTime - self.lastTime
        if (delta >= 1):
            framerate = max(1,int(self.numFrames/delta))
            glfw.set_window_title(self.window, f"Running at {framerate} fps.")
            self.lastTime = self.currentTime
            self.numFrames = -1
            self.frameTime = float(1000.0 / max(1,framerate))
        self.numFrames += 1

    def quit(self):
        
        self.renderer.destroy()

class GraphicsEngine:


    def __init__(self):

        #create assets
        self.shade_texture = Material("gfx/lampshade_photo.jpg")
        self.dark_wood_texture = Material("gfx/dark_wood.jpeg")
        self.marble_texture = Material("gfx/tessellation 2.jpeg")
        self.shade_mesh = Mesh("models/shade_smooth.obj")
        self.base_mesh = Mesh("models/base_smooth.obj")
        self.ground_mesh = Mesh("models/ground.obj")
        self.light_texture = Material("gfx/sky_back.png")
        self.bulb_mesh = Mesh("models/bulb.obj")
        self.moveable_object_texture = Material("gfx/wood.jpeg")
        self.moveable_object_mesh = Mesh("models/cube.obj")

        #initialise opengl
        glClearColor(0.0, 0.0, 0.0, 1)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        glDepthRange(0, 1)
        glDepthMask(GL_TRUE)
        

        #create renderpasses
        self.shaderthreeD = self.createShader("shaders colorbuffer/vertex.txt", "shaders colorbuffer/fragment.txt")
        self.shader = self.createShader("shaders colorbuffer/vertex_light.txt", "shaders colorbuffer/fragment_light.txt")
        self.shadowShader = self.createGeometricShader("shaders colorbuffer/simpleDepthVertex.txt", "shaders colorbuffer/simpleDepthFragment.txt",
                                            "shaders colorbuffer/geometric.txt")

        self.shadowMapResolution = 1028

        self.make_shadow_map()


        self.num = 0
    
    def createShader(self, vertexFilepath, fragmentFilepath):

        with open(vertexFilepath,'r') as f:
            vertex_src = f.readlines()

        with open(fragmentFilepath,'r') as f:
            fragment_src = f.readlines()
        
        shader = compileProgram(compileShader(vertex_src, GL_VERTEX_SHADER),
                                compileShader(fragment_src, GL_FRAGMENT_SHADER), validate = False)
        
        return shader

    def createGeometricShader(self, vertexFilepath, fragmentFilepath, geometricFilepath):
 
        with open(vertexFilepath,'r') as f:
            vertex_src = f.readlines()

        with open(fragmentFilepath,'r') as f:
            fragment_src = f.readlines()

        with open(geometricFilepath,'r') as f:
            geometric_src = f.readlines()
        
        shader = glCreateProgram()

        vert = compileShader(vertex_src, GL_VERTEX_SHADER)
        frag = compileShader(fragment_src, GL_FRAGMENT_SHADER)
        geom = compileShader(geometric_src, GL_GEOMETRY_SHADER)
        
        glAttachShader(shader, vert)
        glAttachShader(shader, frag)
        glAttachShader(shader, geom)

        glLinkProgram(shader)
        
        return shader



    def render(self, scene):
        
        glDisable(GL_BLEND)
        #refresh screen
        glClearColor(1.0, 1.0, 1.0, 1.0)
        glDepthMask(GL_TRUE)

        far_plane = 50

        aspect = self.SHADOW_WIDTH/self.SHADOW_HEIGHT
        shadowProj = pyrr.matrix44.create_perspective_projection(fovy = np.deg2rad(90), aspect = aspect, 
            near = 0.01, far = far_plane,)
        
        lightPos = scene.lights[0].position

        shadow_transforms = [
            shadowProj * pyrr.matrix44.create_look_at(lightPos, lightPos + pyrr.vector3.create(1.0, 0.0, 0.0), 
                                                      pyrr.vector3.create(0.0, -1.0, 0.0)),
            shadowProj * pyrr.matrix44.create_look_at(lightPos, lightPos + pyrr.vector3.create(-1.0, 0.0, 0.0), 
                                                      pyrr.vector3.create(0.0,-1.0, 0.0)),
            shadowProj * pyrr.matrix44.create_look_at(lightPos, lightPos + pyrr.vector3.create(0.0, 1.0, 0.0), 
                                                      pyrr.vector3.create(0.0, 0.0, 1.0)),
            shadowProj * pyrr.matrix44.create_look_at(lightPos, lightPos + pyrr.vector3.create(0.0,-1.0, 0.0), 
                                                      pyrr.vector3.create(0.0, 0.0, -1.0)),
            shadowProj * pyrr.matrix44.create_look_at(lightPos, lightPos + pyrr.vector3.create(0.0, 0.0, 1.0), 
                                                      pyrr.vector3.create(0.0,-1.0, 0.0)),
            shadowProj * pyrr.matrix44.create_look_at(lightPos, lightPos + pyrr.vector3.create(0.0, 0.0,-1.0), 
                                                      pyrr.vector3.create(0.0,-1.0, 0.0))
        ]

        
        glViewport(0, 0, self.SHADOW_WIDTH, self.SHADOW_HEIGHT)
        glBindFramebuffer(GL_FRAMEBUFFER, self.depthMapFBO)
        glUseProgram(self.shadowShader)



        glClearDepth(1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glDepthMask(GL_TRUE)

        i = 0
        while (i < 6):
            glUniformMatrix4fv(
                glGetUniformLocation(self.shadowShader, f"shadowMatrices[{i}]"), 1, GL_FALSE, shadow_transforms[i]
            )
            i = i + 1
        
        glUniform1f(glGetUniformLocation(self.shadowShader, "far_plane"), far_plane)
        glUniform3fv(glGetUniformLocation(self.shadowShader, "lightPos"), 1, lightPos)

        modelmatshadow = glGetUniformLocation(self.shadowShader, "model")


        self.render_base(scene, modelmatshadow)

        self.render_ground(scene, modelmatshadow)

        self.render_shade(scene, modelmatshadow)

        self.render_moveable_object(scene, modelmatshadow)
    

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glUseProgram(0)
        glUseProgram(self.shaderthreeD)

        #then render scene as normal with shadow mapping (using depth cubemap)
        glViewport(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE)

        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClearDepth(1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        
        glUniform1i(glGetUniformLocation(self.shaderthreeD, "imageTexture"), 0)

        projection_transform = pyrr.matrix44.create_perspective_projection(
            fovy = 45, aspect = 640/480, 
            near = 0.1, far = far_plane, dtype=np.float32
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shaderthreeD,"projection"),
            1, GL_FALSE, projection_transform
        )
        modelmatobjloc = glGetUniformLocation(self.shaderthreeD, "model")

        self.viewMatrixLocation = glGetUniformLocation(self.shaderthreeD, "view")
        
        self.lightLocation = {
            "position": glGetUniformLocation(self.shaderthreeD, f"Light.position"),
            "color": glGetUniformLocation(self.shaderthreeD, f"Light.color"),
            "strength":  glGetUniformLocation(self.shaderthreeD, f"Light.strength")
        }
        self.cameraPosLoc = glGetUniformLocation(self.shaderthreeD, "cameraPosition")

        self.specularLoc = glGetUniformLocation(self.shaderthreeD, "specularOn")
        self.twoSidedLoc = glGetUniformLocation(self.shaderthreeD, "twoSided")
        self.depthMapLoc = glGetUniformLocation(self.shaderthreeD, "depthMap")
        self.farPlaneLoc = glGetUniformLocation(self.shaderthreeD, "far_plane")

        glUniform1f(self.farPlaneLoc, far_plane)

        view_transform = pyrr.matrix44.create_look_at(
            eye = scene.player.position,
            target = scene.player.position + scene.player.forwards,
            up = scene.player.up, dtype = np.float32
        )
        glUniformMatrix4fv(self.viewMatrixLocation, 1, GL_FALSE, view_transform)

        glUniform3fv(self.cameraPosLoc, 1, scene.player.position)
        glUniform1i(self.twoSidedLoc, 0)

        glUniform1i(glGetUniformLocation(self.shaderthreeD, "depthMap"), 1)

        glUniform1i(glGetUniformLocation(self.shaderthreeD, "imageTexture"), 0)

        light = scene.lights[0]
        glUniform3fv(self.lightLocation["position"], 1, light.position)
        glUniform3fv(self.lightLocation["color"], 1, light.color)
        glUniform1f(self.lightLocation["strength"], light.strength)

        self.shade_texture.use()
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.depthCubemap)
        glUniform1i(self.twoSidedLoc, 1)
        self.render_shade(scene, modelmatobjloc)

        self.marble_texture.use()
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.depthCubemap)
        glUniform1i(self.twoSidedLoc, 0)
        self.render_base(scene, modelmatobjloc)

        self.dark_wood_texture.use()
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.depthCubemap)
        self.render_ground(scene, modelmatobjloc)

        self.moveable_object_texture.use()
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_CUBE_MAP, self.depthCubemap)
        self.render_moveable_object(scene, modelmatobjloc)

        glUseProgram(self.shader) #Render translucent object
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        projection_transform = pyrr.matrix44.create_perspective_projection(
            fovy = 45, aspect = 640/480, 
            near = 0.1, far = far_plane, dtype=np.float32
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader,"projection"),
            1, GL_FALSE, projection_transform
        )
        modelmatobjloc2 = glGetUniformLocation(self.shader, "model")
        self.viewMatrixLocation = glGetUniformLocation(self.shader, "view")
        self.tintLoc = glGetUniformLocation(self.shader, "tint")

        view_transform = pyrr.matrix44.create_look_at(
            eye = scene.player.position,
            target = scene.player.position + scene.player.forwards,
            up = scene.player.up, dtype = np.float32
        )
        glUniformMatrix4fv(self.viewMatrixLocation, 1, GL_FALSE, view_transform)
        
        light = scene.lights[0]

        glUniform3fv(self.tintLoc, 1, light.color)
        self.light_texture.use()
        self.render_bulb(scene, modelmatobjloc2)
        glFlush()
        if self.num < 2:
            print(glGetError())
            self.num += 1

    def render_base(self, scene, modelloc):
        base = scene.base
        model_transform = pyrr.matrix44.create_identity(dtype=np.float32)
        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_eulers(
                eulers=np.radians(base.eulers), dtype=np.float32
            )
        )
        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_translation(
                vec=np.array(base.position),dtype=np.float32
            )
        )
        glUniformMatrix4fv(modelloc,1,GL_FALSE,model_transform)
        glBindVertexArray(self.base_mesh.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.base_mesh.vertex_count)
        #glBindVertexArray(0)

    def render_shade(self, scene, modelloc):
        shade = scene.shade
        model_transform = pyrr.matrix44.create_identity(dtype=np.float32)
        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_eulers(
                eulers=np.radians(shade.eulers), dtype=np.float32
            )
        )
        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_translation(
                vec=np.array(shade.position),dtype=np.float32
            )
        )
        glUniformMatrix4fv(modelloc,1,GL_FALSE,model_transform)
        glBindVertexArray(self.shade_mesh.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.shade_mesh.vertex_count)
        #glBindVertexArray(0)

    def render_bulb(self, scene, modelloc):
        bulb = scene.bulb
        model_transform = pyrr.matrix44.create_identity(dtype=np.float32)
        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_eulers(
                eulers=np.radians(bulb.eulers), dtype=np.float32
            )
        )
        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_translation(
                vec=np.array(bulb.position),dtype=np.float32
            )
        )
        glUniformMatrix4fv(modelloc,1,GL_FALSE,model_transform)
        glBindVertexArray(self.bulb_mesh.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.bulb_mesh.vertex_count)
        #glBindVertexArray(0)


    def render_ground(self, scene, modelloc):
        ground = scene.ground
        model_transform = pyrr.matrix44.create_identity(dtype=np.float32)
        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_eulers(
                eulers=np.radians(ground.eulers), dtype=np.float32
            )
        )
        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_translation(
                vec=np.array(ground.position),dtype=np.float32
            )
        )
        glUniformMatrix4fv(modelloc,1,GL_FALSE,model_transform)
        glBindVertexArray(self.ground_mesh.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.ground_mesh.vertex_count)
        #glBindVertexArray(0)
    
    def render_moveable_object(self, scene, modelloc):
        moveable = scene.moveable_object
        model_transform = pyrr.matrix44.create_identity(dtype=np.float32)
        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_eulers(
                eulers=np.radians(moveable.eulers), dtype=np.float32
            )
        )
        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_translation(
                vec=np.array(moveable.position),dtype=np.float32
            )
        )
        glUniformMatrix4fv(modelloc,1,GL_FALSE,model_transform)
        glBindVertexArray(self.moveable_object_mesh.vao)
        glDrawArrays(GL_TRIANGLES, 0, self.moveable_object_mesh.vertex_count)
        #glBindVertexArray(0)



    def make_shadow_map(self):
        self.SHADOW_WIDTH = 100
        self.SHADOW_HEIGHT = 100
        self.depthMapFBO = glGenFramebuffers(1)
        self.depthCubemap = glGenTextures(1)

        glBindTexture(GL_TEXTURE_CUBE_MAP, self.depthCubemap)
        

        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_BASE_LEVEL, 0)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAX_LEVEL, 0)

        i = 0
        while (i < 6):
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, GL_RGBA16F, 
                     self.SHADOW_WIDTH, self.SHADOW_HEIGHT, 0, GL_RGBA, GL_FLOAT, 0)
            i = i + 1

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glBindFramebuffer(GL_FRAMEBUFFER, self.depthMapFBO)

        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, self.depthCubemap, 0) 

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)    
        glDrawBuffers([GL_COLOR_ATTACHMENT0])

        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            print("oh no!!")
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
    

    def destroy(self):

        self.shade_texture.destroy()
        self.dark_wood_texture.destroy()
        self.marble_texture.destroy()
        self.shade_mesh.destroy()
        self.base_mesh.destroy()
        self.ground_mesh.destroy()
        self.bulb_mesh.destroy()
        self.light_texture.destroy()

        self.moveable_object_texture.destroy()
        self.moveable_object_mesh.destroy()
        glDeleteProgram(self.shader)
        glDeleteProgram(self.shaderthreeD)
        glDeleteProgram(self.shadowShader)
        glDeleteBuffers(1, self.depthMapFBO)
        glDeleteTextures(1, self.depthCubemap)

class Mesh:


    def __init__(self, filename):
        # x, y, z, s, t, nx, ny, nz
        self.vertices = self.loadMesh(filename)
        self.vertex_count = len(self.vertices)//8
        self.vertices = np.array(self.vertices, dtype=np.float32)

        self.vao = glGenVertexArrays(1)
        
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)

        glBindVertexArray(self.vao)
        #position
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(0))
        #texture
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(12))
        #normal
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(20))
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
    
    def loadMesh(self, filename):

        #raw, unassembled data
        v = []
        vt = []
        vn = []
        
        #final, assembled and packed result
        vertices = []

        #open the obj file and read the data
        with open(filename,'r') as f:
            line = f.readline()
            while line:
                firstSpace = line.find(" ")
                flag = line[0:firstSpace]
                if flag=="v":
                    #vertex
                    line = line.replace("v ","")
                    line = line.split(" ")
                    l = [float(x) for x in line]
                    v.append(l)
                elif flag=="vt":
                    #texture coordinate
                    line = line.replace("vt ","")
                    line = line.split(" ")
                    l = [float(x) for x in line]
                    vt.append(l)
                elif flag=="vn":
                    #normal
                    line = line.replace("vn ","")
                    line = line.split(" ")
                    l = [float(x) for x in line]
                    vn.append(l)
                elif flag=="f":
                    #face, three or more vertices in v/vt/vn form
                    line = line.replace("f ","")
                    line = line.replace("\n","")
                    #get the individual vertices for each line
                    line = line.split(" ")
                    faceVertices = []
                    faceTextures = []
                    faceNormals = []
                    for vertex in line:
                        #break out into [v,vt,vn],
                        #correct for 0 based indexing.
                        l = vertex.split("/")
                        position = int(l[0]) - 1
                        faceVertices.append(v[position])
                        texture = int(l[1]) - 1
                        faceTextures.append(vt[texture])
                        normal = int(l[2]) - 1
                        faceNormals.append(vn[normal])
                    # obj file uses triangle fan format for each face individually.
                    # unpack each face
                    triangles_in_face = len(line) - 2

                    vertex_order = []
                    """
                        eg. 0,1,2,3 unpacks to vertices: [0,1,2,0,2,3]
                    """
                    for i in range(triangles_in_face):
                        vertex_order.append(0)
                        vertex_order.append(i+1)
                        vertex_order.append(i+2)
                    for i in vertex_order:
                        for x in faceVertices[i]:
                            vertices.append(x)
                        for x in faceTextures[i]:
                            vertices.append(x)
                        for x in faceNormals[i]:
                            vertices.append(x)
                line = f.readline()
        return vertices
    
    def destroy(self):
        glDeleteVertexArrays(1, (self.vao,))
        glDeleteBuffers(1,(self.vbo,))

class Material:


    def __init__(self, filepath):
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        with Image.open(filepath, mode = "r") as img:
            image_width,image_height = img.size
            img = img.convert("RGBA")
            img_data = bytes(img.tobytes())
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,image_width,image_height,0,GL_RGBA,GL_UNSIGNED_BYTE,img_data)
        glGenerateMipmap(GL_TEXTURE_2D)

    def use(self):
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D,self.texture)

    def destroy(self):
        glDeleteTextures(1, (self.texture,))

window = initialize_glfw()
myApp = App(window)