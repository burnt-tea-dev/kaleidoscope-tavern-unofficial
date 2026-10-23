package org.senluo.oracle;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;
import java.lang.reflect.*;
import java.io.*;
import java.security.*;
import com.google.gson.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;
import jdk.internal.org.objectweb.asm.commons.*;
import jdk.internal.org.objectweb.asm.util.*;

/** External, narrow original-bytecode experiment; no color formula is implemented here. */
public final class PotionColorOracle {
  static final Gson JSON=new GsonBuilder().setPrettyPrinting().disableHtmlEscaping().create();
  static final String PREFIX="org/senluo/oracle/PotionColorOracle$";
  static final Map<String,String> TYPES=new LinkedHashMap<>();
  static final Map<String,Object> POTIONS=new LinkedHashMap<>();
  static final Map<String,EffectDef> EFFECTS=new LinkedHashMap<>();
  static final List<Map<String,Object>> PROOFS=new ArrayList<>();
  static Path jar,out;
  static {
    for(var p:new String[][]{{"cwu","ActualContents"},{"cwv","ActualPotions"},{"cws","ActualPotion"},{"bsb","EffectFields"},{"brz","ActualInstance"},{"brz$a","BlendState"},{"brx","EffectDef"},{"jm","Holder"},{"cpn","Features"},{"cpl","FlagSet"},{"ayo","ActualMath"},{"axy$b","ActualColor"}})TYPES.put(p[0],PREFIX+p[1]);
  }
  public interface Holder {Object a();}
  public record Held(Object value) implements Holder {public Object a(){return value;}}
  public static final class EffectDef {
    final String id;final int color;
    EffectDef(String id,int color){this.id=id;this.color=color;}
    public int g(){return color;}
  }
  public static final class BlendState {public BlendState(){}}
  public static final class FlagSet {}
  public static final class Features {public static final FlagSet f=new FlagSet();}
  public static Holder register(String id,Object potion){if(POTIONS.put(id,potion)!=null)throw new AssertionError("duplicate "+id);return new Held(potion);}
  static String sha(byte[] b)throws Exception{return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b));}
  static byte[] member(String name)throws Exception{try(var z=new ZipFile(jar.toFile())){return z.getInputStream(z.getEntry(name+".class")).readAllBytes();}}
  static ClassNode read(String name)throws Exception{var n=new ClassNode();new ClassReader(member(name)).accept(n,0);return n;}
  static String trace(MethodNode m){var t=new Textifier();m.accept(new TraceMethodVisitor(t));var s=new StringWriter();t.print(new PrintWriter(s));return s.toString();}
  static MethodNode remap(MethodNode m,Map<String,String> mappings){var r=new SimpleRemapper(mappings);var n=new MethodNode(Opcodes.ASM8,m.access,m.name,r.mapMethodDesc(m.desc),null,null);m.accept(new MethodRemapper(n,r));return n;}
  static void prove(String owner,MethodNode m)throws Exception{
    var inv=new HashMap<String,String>();TYPES.forEach((a,b)->inv.put(b,a));
    String source=trace(m),round=trace(remap(remap(m,TYPES),inv));
    if(!source.equals(round))throw new AssertionError("changed original instructions "+owner+"."+m.name+m.desc);
    String filename=owner.replace('$','_')+"-"+PROOFS.size()+".original.asm.txt";
    Files.writeString(out.resolve(filename),source);
    PROOFS.add(Map.of("owner",owner,"method",m.name,"descriptor",m.desc,"instruction_trace_sha256",sha(source.getBytes(java.nio.charset.StandardCharsets.UTF_8)),"inverse_remap_equal",true,"trace",filename));
  }
  static byte[] extract(String owner,java.util.function.Predicate<MethodNode> methods,Set<String> fields)throws Exception{
    var n=read(owner);n.interfaces.clear();n.signature=null;n.innerClasses.clear();n.nestMembers=null;n.nestHostClass=null;
    n.methods.removeIf(m->!methods.test(m));n.fields.removeIf(f->!fields.contains(f.name));
    for(var m:n.methods)prove(owner,m);
    var w=new ClassWriter(0);n.accept(new ClassRemapper(w,new SimpleRemapper(TYPES)));return w.toByteArray();
  }
  static byte[] actualPotions()throws Exception{
    var n=read("cwv");n.interfaces.clear();n.signature=null;n.innerClasses.clear();n.nestMembers=null;n.nestHostClass=null;
    n.methods.removeIf(m->!m.name.equals("<clinit>"));prove("cwv",n.methods.get(0));
    var m=new MethodNode(Opcodes.ACC_PRIVATE|Opcodes.ACC_STATIC,"a","(Ljava/lang/String;Lcws;)Ljm;",null,null);
    m.visitCode();m.visitVarInsn(Opcodes.ALOAD,0);m.visitVarInsn(Opcodes.ALOAD,1);
    m.visitMethodInsn(Opcodes.INVOKESTATIC,"org/senluo/oracle/PotionColorOracle","register","(Ljava/lang/String;Ljava/lang/Object;)L"+PREFIX+"Holder;",false);
    m.visitInsn(Opcodes.ARETURN);m.visitMaxs(2,2);m.visitEnd();n.methods.add(m);
    var w=new ClassWriter(0);n.accept(new ClassRemapper(w,new SimpleRemapper(TYPES)));return w.toByteArray();
  }
  static Map<String,EffectDef> effectFields()throws Exception{
    var n=read("bsb");var m=n.methods.stream().filter(x->x.name.equals("<clinit>")).findFirst().orElseThrow();
    Files.writeString(out.resolve("bsb-original-clinit.asm.txt"),trace(m));
    var fields=new LinkedHashMap<String,EffectDef>();String id=null;Integer color=null;boolean afterCategory=false;int registrationCalls=0;
    for(var ins:m.instructions){
      if(id==null&&ins instanceof LdcInsnNode ldc&&ldc.cst instanceof String s){id=s;}
      if(ins instanceof FieldInsnNode f&&f.getOpcode()==Opcodes.GETSTATIC&&f.owner.equals("bry")){afterCategory=true;}
      else if(afterCategory&&ins.getOpcode()>=0){
        if(!(ins instanceof LdcInsnNode ldc&&ldc.cst instanceof Integer))throw new AssertionError("expected source color integer after category for "+id);
        color=(Integer)((LdcInsnNode)ins).cst;afterCategory=false;
      }
      if(ins instanceof MethodInsnNode call&&call.owner.equals("bsb")&&call.name.equals("a")&&call.desc.equals("(Ljava/lang/String;Lbrx;)Ljm;"))registrationCalls++;
      if(ins instanceof FieldInsnNode f&&f.getOpcode()==Opcodes.PUTSTATIC&&f.owner.equals("bsb")){
        if(id==null||color==null)throw new AssertionError("missing source effect definition");
        var effect=new EffectDef(id,color);if(fields.put(f.name,effect)!=null||EFFECTS.put(id,effect)!=null)throw new AssertionError("duplicate effect");id=null;color=null;
      }
    }
    if(registrationCalls!=fields.size()||fields.size()!=39)throw new AssertionError("effect registry extraction incomplete: "+fields.size());
    return fields;
  }
  static byte[] generatedEffectFields(Set<String> fields){
    var w=new ClassWriter(0);w.visit(Opcodes.V21,Opcodes.ACC_PUBLIC|Opcodes.ACC_FINAL,PREFIX+"EffectFields",null,"java/lang/Object",null);
    for(var f:fields)w.visitField(Opcodes.ACC_PUBLIC|Opcodes.ACC_STATIC,f,"L"+PREFIX+"Holder;",null,null).visitEnd();w.visitEnd();return w.toByteArray();
  }
  static class Loader extends ClassLoader{
    final Map<String,byte[]> generated;
    Loader(Map<String,byte[]> x){super(PotionColorOracle.class.getClassLoader());generated=x;}
    protected Class<?> findClass(String name)throws ClassNotFoundException{var b=generated.get(name);if(b==null)throw new ClassNotFoundException(name);return defineClass(name,b,0,b.length);}
  }
  static void put(Map<String,byte[]> classes,String name,byte[] bytes){classes.put(TYPES.get(name).replace('/','.'),bytes);}
  static Object invoke(Object target,String method)throws Exception{return target.getClass().getMethod(method).invoke(target);}
  static Map<String,Object> observed(String id,Object potion,Object contents,java.lang.reflect.Method color,java.lang.reflect.Method optional)throws Exception{
    @SuppressWarnings("unchecked")var effects=(List<Object>)invoke(potion,"a");var inputs=new ArrayList<Map<String,Object>>();
    for(Object effect:effects){var held=(Holder)invoke(effect,"c");var def=(EffectDef)held.a();inputs.add(Map.of("id",def.id,"amplifier",invoke(effect,"e"),"duration_ticks",invoke(effect,"d"),"visible",invoke(effect,"g"),"effect_rgb",def.color,"effect_hex",String.format("#%06X",def.color)));}
    int value=(int)color.invoke(contents);var result=new LinkedHashMap<String,Object>();result.put("id",id);result.put("effects",inputs);result.put("argb_signed",value);result.put("rgb",value&0xffffff);result.put("hex",String.format("#%06X",value&0xffffff));
    var opt=(OptionalInt)optional.invoke(null,effects);result.put("optional_present",opt.isPresent());result.put("optional_argb_signed",opt.isPresent()?opt.getAsInt():null);return result;
  }
  public static void main(String[] args)throws Exception{
    jar=Path.of(args[0]);out=Path.of(args[1]);Files.createDirectories(out);
    var fields=effectFields();var classes=new LinkedHashMap<String,byte[]>();
    put(classes,"bsb",generatedEffectFields(fields.keySet()));
    put(classes,"cws",extract("cws",m->m.name.equals("<init>")||(m.name.equals("a")&&m.desc.equals("()Ljava/util/List;")),Set.of("c","d","e")));
    put(classes,"brz",extract("brz",m->(m.name.equals("<init>")&&m.desc.startsWith("(Ljm;")&&!m.desc.contains("Lbrz$b;"))||Set.of("c()Ljm;","d()I","e()I","g()Z").contains(m.name+m.desc),Set.of("g","h","i","j","k","l","m","n")));
    put(classes,"ayo",extract("ayo",m->m.name.equals("a")&&m.desc.equals("(III)I"),Set.of()));
    put(classes,"axy$b",extract("axy$b",m->Set.of("b(I)I","c(I)I","d(I)I","a(III)I","a(IIII)I").contains(m.name+m.desc),Set.of()));
    put(classes,"cwu",extract("cwu",m->Set.of("<init>(Ljava/util/Optional;Ljava/util/Optional;Ljava/util/List;)V","a()Ljava/lang/Iterable;","b()I","c(Ljm;)I","a(Ljava/lang/Iterable;)I","b(Ljava/lang/Iterable;)Ljava/util/OptionalInt;").contains(m.name+m.desc),Set.of("d","e","f")));
    put(classes,"cwv",actualPotions());
    var loader=new Loader(classes);Class<?> effectFields=loader.loadClass(TYPES.get("bsb").replace('/','.'));
    for(var e:fields.entrySet())effectFields.getField(e.getKey()).set(null,new Held(e.getValue()));
    Class.forName(TYPES.get("cwv").replace('/','.'),true,loader);
    Class<?> contentsClass=loader.loadClass(TYPES.get("cwu").replace('/','.'));
    var ctor=contentsClass.getConstructor(Optional.class,Optional.class,List.class);var color=contentsClass.getMethod("b");var optional=contentsClass.getMethod("b",Iterable.class);
    var rows=new ArrayList<Map<String,Object>>();
    for(var e:POTIONS.entrySet())rows.add(observed(e.getKey(),e.getValue(),ctor.newInstance(Optional.of(new Held(e.getValue())),Optional.empty(),List.of()),color,optional));
    Object noPotion=ctor.newInstance(Optional.empty(),Optional.empty(),List.of());int emptyColor=(int)color.invoke(noPotion);
    var instance=loader.loadClass(TYPES.get("brz").replace('/','.'));var instanceCtor=instance.getConstructor(Holder.class,int.class,int.class,boolean.class,boolean.class);
    var wither=instanceCtor.newInstance(new Held(EFFECTS.get("wither")),900,1,false,true);
    int witherColor=(int)color.invoke(ctor.newInstance(Optional.empty(),Optional.empty(),List.of(wither)));
    Object hidden=instanceCtor.newInstance(new Held(EFFECTS.get("poison")),900,0,false,false);
    var controls=new LinkedHashMap<String,Object>();controls.put("empty_contents",Map.of("argb_signed",emptyColor,"rgb",emptyColor&0xffffff,"hex",String.format("#%06X",emptyColor&0xffffff)));
    controls.put("hidden_only",Map.of("getColor",color.invoke(ctor.newInstance(Optional.empty(),Optional.empty(),List.of(hidden))),"optional_present",((OptionalInt)optional.invoke(null,List.of(hidden))).isPresent()));
    controls.put("custom_color",Map.of("input",0x123456,"observed",color.invoke(ctor.newInstance(Optional.empty(),Optional.of(0x123456),List.of(wither)))));
    controls.put("bedrock_wither_adaptation",Map.of("scope","Java has WITHER MobEffect but no vanilla WITHER potion registry entry; apply original Java PotionContents to that effect, not claim author potion parity","effect_id","wither","argb_signed",witherColor,"rgb",witherColor&0xffffff,"hex",String.format("#%06X",witherColor&0xffffff)));
    var defs=new ArrayList<Map<String,Object>>();for(var e:fields.entrySet())defs.add(Map.of("obfuscated_field",e.getKey(),"id",e.getValue().id,"rgb",e.getValue().color,"hex",String.format("#%06X",e.getValue().color)));
    var source=new LinkedHashMap<String,Object>();source.put("minecraft_client_jar",jar.toString());source.put("minecraft_client_jar_sha256",sha(Files.readAllBytes(jar)));var byteHashes=new LinkedHashMap<String,String>();for(String c:List.of("cwu","cwv","cws","brz","bsb","axy$b","ayo"))byteHashes.put(c,sha(member(c)));source.put("original_class_sha256",byteHashes);
    Files.writeString(out.resolve("instruction-roundtrip.json"),JSON.toJson(Map.of("type_remapping",TYPES,"methods",PROOFS,"all_equal",true))+"\n");
    Files.writeString(out.resolve("java-potion-colors.json"),JSON.toJson(Map.of("schema",1,"source",source,"scope","Minecraft 1.21.1 original PotionContents methods + original Potions registry initializer, Potion constructors, MobEffectInstance constructors/accessors, Mth clamp and FastColor ARGB32 methods. Registry/Holder, MobEffect color getter, unused feature and blend state are narrow fixtures. This is numeric source execution, not client/render/BDS validation.","java_potions",rows,"mob_effect_colors",defs,"controls",controls))+"\n");
    System.out.println("Original Java potion registrations="+rows.size()+", effects="+defs.size()+", preserved original methods="+PROOFS.size());
    for(var row:rows)System.out.println(row.get("id")+"="+row.get("hex")+" ("+row.get("argb_signed")+")");
    System.out.println("empty="+controls.get("empty_contents")+"; wither="+controls.get("bedrock_wither_adaptation"));
  }
}
