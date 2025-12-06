//Script to select and stream RGB frames from multiple RealSense cameras in Unity
using UnityEngine;
using Intel.RealSense;
using System.Collections.Generic;

public class RealSense_RGB_MultiCamera : MonoBehaviour
{
    [Header("Which RealSense to open? 0 = first, 1 = second")]
    public int deviceIndex = 0;

    Pipeline pipeline;
    Texture2D texture;
    Renderer quadRenderer;

    const int WIDTH = 640;
    const int HEIGHT = 480;
    const int FPS = 30;

    void Start()
    {
        quadRenderer = GetComponent<Renderer>();

        // Detect all RealSense devices
        List<string> deviceSerials = new List<string>();
        using (var ctx = new Context())
        {
            foreach (var dev in ctx.QueryDevices())
            {
                string serial = dev.Info[CameraInfo.SerialNumber];
                deviceSerials.Add(serial);
                Debug.Log("RealSense Found: " + serial);
            }
        }

        // Safety
        if (deviceSerials.Count == 0)
        {
            Debug.LogError("No RealSense cameras detected!");
            return;
        }

        // Clamp to available devices
        deviceIndex = Mathf.Clamp(deviceIndex, 0, deviceSerials.Count - 1);
        string selectedSerial = deviceSerials[deviceIndex];
        Debug.Log("USING DEVICE: " + selectedSerial);

        // Start RGB pipeline
        pipeline = new Pipeline();
        var config = new Config();
        config.EnableDevice(selectedSerial);
        config.EnableStream(Stream.Color, WIDTH, HEIGHT, Format.Any, FPS);
        pipeline.Start(config);

        texture = new Texture2D(WIDTH, HEIGHT, TextureFormat.RGB24, false);
    }

    void Update()
    {
        using (var frames = pipeline.WaitForFrames())
        using (var colorFrame = frames.ColorFrame)
        {
            byte[] raw = new byte[colorFrame.DataSize];
            colorFrame.CopyTo(raw);

            Format format = colorFrame.Profile.Format;

            if (format == Format.Rgb8)                      // Good
                texture.LoadRawTextureData(raw);

            else if (format == Format.Bgr8)                 // Blue tint fix
            {
                for (int i = 0; i < raw.Length; i += 3)
                {
                    byte t = raw[i];
                    raw[i] = raw[i + 2];
                    raw[i + 2] = t;
                }
                texture.LoadRawTextureData(raw);
            }

            else if (format == Format.Yuyv)                 // YUV → RGB conversion
            {
                byte[] rgb = new byte[WIDTH * HEIGHT * 3];
                int k = 0;

                for (int i = 0; i < raw.Length; i += 4)
                {
                    int y0 = raw[i + 0];
                    int u  = raw[i + 1] - 128;
                    int y1 = raw[i + 2];
                    int v  = raw[i + 3] - 128;

                    rgb[k++] = clamp(y0 + 1.402f * v);
                    rgb[k++] = clamp(y0 - 0.344f * u - 0.714f * v);
                    rgb[k++] = clamp(y0 + 1.772f * u);

                    rgb[k++] = clamp(y1 + 1.402f * v);
                    rgb[k++] = clamp(y1 - 0.344f * u - 0.714f * v);
                    rgb[k++] = clamp(y1 + 1.772f * u);
                }

                texture.LoadRawTextureData(rgb);
            }

            texture.Apply();
            quadRenderer.material.mainTexture = texture;
        }
    }

    byte clamp(float x) => (byte)Mathf.Clamp(x, 0, 255);

    void OnApplicationQuit()
    {
        pipeline.Stop();
        pipeline.Dispose();
    }
}
