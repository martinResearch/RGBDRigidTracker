vertex_shader_source = """
                        uniform mat4 Mvp;

                        in vec3 in_vert;
                        in vec3 in_norm;
                        in vec3 in_text;

                        out vec3 v_vert;
                        out vec3 v_norm;
                        out vec3 v_text;

                        void main() {
                                v_vert = in_vert;
                                v_norm = in_norm;
                                v_text = in_text;
                                gl_Position = Mvp * vec4(v_vert, 1.0);
                        }
                        """

fragment_shader_RGB_source = """uniform sampler2D Texture;
                                uniform vec4 Color;
                                uniform vec3 Light;

                                in vec3 v_vert;
                                in vec3 v_norm;
                                in vec3 v_text;

                                out vec4 f_color;

                                void main() {
                                        float lum = dot(normalize(v_norm), normalize(v_vert - Light));
                                        lum = acos(lum) / 3.14159265;
                                        lum = clamp(lum, 0.0, 1.0);
                                        lum = lum * lum;
                                        lum = smoothstep(0.0, 1.0, lum);

                                        lum *= smoothstep(0.0, 80.0, v_vert.z) * 0.3 + 0.7;

                                        lum = lum * 0.3 + 0.7;

                                        vec3 color = texture(Texture, v_text.xy).rgb;
                                        color = color * (1.0 - Color.a) + Color.rgb * Color.a;
                                        f_color = vec4(color * lum, 1.0);
                                }"""
fragment_shader_XYZ_source="""
                            in vec3 v_vert;
                            in vec3 v_norm;
                            in vec3 v_text;
                            uniform vec3 boxmin;
                            uniform vec3 boxmax;
                            out vec4 f_color;

                            void main() {
                                    f_color=vec4((v_vert-boxmin)/(boxmax-boxmin), 1);

                            }"""
fragment_shader_Depth_source="""
                            in vec3 v_vert;
                            in vec3 v_norm;
                            in vec3 v_text;
                            uniform vec3 boxmin;
                            uniform vec3 boxmax;
                            out vec4 f_color;

                            void main() {
                                    f_color=vec4((v_vert-boxmin)/(boxmax-boxmin), 1);

                            }"""