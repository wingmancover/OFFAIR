using UnrealSharp.Attributes;
using UnrealSharp.Engine;

namespace Offair.Managed;

/// <summary>
/// Isolated integration probe. No gameplay state, timers or static UObject references.
/// Each actor starts at zero and is discarded with its world.
/// </summary>
[UClass]
public partial class AOffairScriptProbe : AActor
{
    [UProperty(PropertyFlags.BlueprintReadOnly)]
    public partial int CallCount { get; set; }

    [UFunction(FunctionFlags.BlueprintCallable)]
    public int RoundTrip(int value)
    {
        CallCount++;
        return value + 1;
    }
}
