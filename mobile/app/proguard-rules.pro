# kotlinx.serialization giữ lại serializer sinh ra lúc biên dịch.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class vn.t176.patrol.** {
    *** Companion;
}
-keepclasseswithmembers class vn.t176.patrol.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# Bất biến §4: không log payload ở bản release.
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
}
